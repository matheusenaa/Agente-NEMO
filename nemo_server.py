"""
NEMO IDE — Servidor de API (FastAPI)

Serve a API de chat/agentes/arquivos/terminal da NEMO IDE e, em produção
(apos `npm run build` do dashboard), também serve o frontend compilado.

Endpoints principais
--------------------
GET  /api/nemo/health                 -> status do servidor e chave OpenRouter
GET  /api/nemo/context                -> visao geral do projeto (agentes, squads, skills, modelos)
GET  /api/nemo/agents                 -> lista de agentes (parse dos .agent.md)
POST /api/nemo/chat                   -> conversa com um agente (via OpenRouterClient)
GET  /api/nemo/files?path=            -> listagem segura de diretorio
GET  /api/nemo/file?path=             -> conteudo de arquivo
POST /api/nemo/file/save              -> salvar arquivo
POST /api/nemo/terminal               -> executar comando (com guarda de comandos destrutivos)
GET  /api/nemo/snapshot               -> snapshot de squads (fallback de producao do squadWatcher)
GET  /  (produção)                    -> frontend compilado (dashboard/dist)

Uso:
    python nemo_server.py                # development, host 127.0.0.1:8798
    python nemo_server.py --port 8798    # porta customizada
    python nemo_server.py --no-dashboard # nao tenta servir o build do frontend
    uvicorn nemo_server:app ...          # producao (Render/Railway) — dashboard servido na raiz '/'

Variaveis de ambiente:
    PORT            → porta do servidor (usado em producao; ex.: Render define PORT)
    HOST            → host para bind (default 127.0.0.1 em dev)
    CORS_ORIGINS    → origens permitidas separadas por virgula (extra alem dos locais)
    OPENROUTER_*    → chave e cabecalhos do OpenRouter (ver .env.example)
"""

from __future__ import annotations

import io
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Garante que a raiz do projeto esteja no sys.path independente do ambiente
def _get_project_root() -> Path:
    """Retorna a raiz do projeto funcionando tanto em dev quanto frozen (PyInstaller).

    Modo frozen (PyInstaller one-folder): os dados do projeto (agents/, squads/,
    skills/, dashboard/dist, models_config.py, .env.example) são copiados para
    dentro do diretório _internal/, que é exatamente sys._MEIPASS. Portanto a
    "raiz do projeto" em frozen é sys._MEIPASS (e NÃO o seu parent, que resolve
    para um diretório errado).
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
        # Fallback robusto: se o pacote de dados não estiver em MEIPASS,
        # procura por agents/ nas proximidades (onedir em outras layouts).
        if not (base / "agents").is_dir():
            for cand in (base.parent, base.parent / "_MEIPASS", Path.cwd()):
                if (cand / "agents").is_dir():
                    base = cand
                    break
        return base
    return Path(__file__).resolve().parent

ROOT = _get_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from openrouter_client import OpenRouterClient, CompletionResult
from models_config import OPENROUTER_MODELS, get_model_by_id, get_all_models

# ---------------------------------------------------------------------------
# Constantes e helpers
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
PROJECT_NAME = "NEMO IDE"

AGENTS_DIR = ROOT / "agents"
SQUADS_DIR = ROOT / "squads"
SKILLS_DIR = ROOT / "skills"
DASHBOARD_DIST = ROOT / "dashboard" / "dist"
DATA_DIR = ROOT / "_data"
EVENTS_FILE = DATA_DIR / "events.json"

DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "8798"))

# Modelo padrão por categoria de agente (economia consciente por padrão)
CATEGORY_MODEL_DEFAULT = "deepseek/deepseek-chat"
CATEGORY_MODEL_MAP: Dict[str, str] = {
    "assistant": "deepseek/deepseek-chat",
    "data": "deepseek/deepseek-chat",
    "writing": "openai/gpt-4o-mini",
    "research": "deepseek/deepseek-chat",
    "review": "openai/gpt-4o-mini",
    "seo": "openai/gpt-4o-mini",
    "design": "openai/gpt-4o-mini",
    "video": "openai/gpt-4o-mini",
    "publishing": "openai/gpt-4o-mini",
    "social": "openai/gpt-4o-mini",
    "strategy": "openai/gpt-4o-mini",
    "technology": "openai/gpt-4o",
}

ICON_BY_CATEGORY: Dict[str, str] = {
    "assistant": "🐟",
    "data": "📊",
    "writing": "✍️",
    "research": "🔍",
    "review": "✅",
    "seo": "🔎",
    "design": "🎨",
    "video": "🎬",
    "publishing": "📤",
    "social": "📱",
    "strategy": "🎯",
    "technology": "🛠️",
}

# Comandos proibidos / destrutivos — exigem confirmacao explicita (force=true)
DESTRUCTIVE_PATTERNS = [
    r"(^|\s|&|\||;)(rm|rmdir|del|erase|format|mkfs|fdisk|shutdown|reboot)\b",
    r"Remove-Item",
    r"(^|\s)git\s+push\s+(-f|--force)",
    r"(^|\s)git\s+reset\s+--hard",
    r"(^|\s)git\s+clean\s+(-f|-x|--force)",
    r"DROP\s+(TABLE|DATABASE|SCHEMA)",
    r"(^|\s)rd\s+/s",
]

MAX_TERMINAL_TIMEOUT = 120  # segundos


def slugify(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9 _\-]", "", value).lower().strip().replace(" ", "-")


def _read_frontmatter(path: Path) -> Dict[str, Any]:
    """Extrai os campos principais do frontmatter YAML dos arquivos .agent.md."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    meta: Dict[str, Any] = {"file": path.name, "id": path.stem.replace(".agent", "") if path.stem.endswith("agent") else path.stem}
    if not raw.startswith("---"):
        return meta
    end = raw.find("\n---", 3)
    if end == -1:
        return meta
    fm = raw[3:end]
    basic_fields: Dict[str, str] = {
        "name": r"^\s*name\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
        "title": r"^\s*title\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
        "icon": r"^\s*icon\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
        "category": r"^\s*category\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
        "version": r"^\s*version\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
        "execution": r"^\s*execution\s*[:=]?\s*[\"']?(?P<v>[^\"'\n\r]+)",
    }
    for key, pattern in basic_fields.items():
        m = re.search(pattern, fm, re.MULTILINE)
        if m:
            meta[key] = m.group("v").strip()
    # descricao em PT-BR (marca | ou texto)
    m = re.search(r"description_pt-?BR:\s*\|\s*\n(?P<desc>(?:.*\n?)+?)(?=\n\S|$)", fm, re.MULTILINE)
    meta["role"] = ""
    if m:
        meta["role"] = " ".join(line.strip() for line in m.group("desc").splitlines() if line.strip()).strip()
    if not meta.get("role"):
        m = re.search(r"description:\s*\|\s*\n(?P<desc>(?:.*\n?)+?)(?=\n\S|$)", fm, re.MULTILINE)
        if m:
            meta["role"] = " ".join(line.strip() for line in m.group("desc").splitlines() if line.strip()).strip()
    # corpo markdown (persona)
    body = raw[end + 4:]
    meta["body"] = body.strip()
    meta["description_pt-BR"] = meta.get("role", "")
    return meta


def _discover_agents() -> List[Dict[str, Any]]:
    agents: List[Dict[str, Any]] = []
    if not AGENTS_DIR.is_dir():
        return agents
    for path in sorted(AGENTS_DIR.glob("*.agent.md")):
        meta = _read_frontmatter(path)
        category = meta.get("category", "assistant")
        agents.append({
            "id": meta.get("id", path.stem),
            "name": meta.get("name", path.stem),
            "title": meta.get("title", "Agente"),
            "icon": meta.get("icon", ICON_BY_CATEGORY.get(category, "🤖")),
            "category": category,
            "role": meta.get("role", ""),
            "version": meta.get("version", "1.0.0"),
            "file": str(path),
            "defaultModel": CATEGORY_MODEL_MAP.get(category, CATEGORY_MODEL_DEFAULT),
        })
    return agents


def _agent_persona(agent_id: str) -> Optional[Dict[str, Any]]:
    for agent in _discover_agents():
        if agent["id"] == agent_id:
            return agent
    # fallback: NEMO
    for agent in _discover_agents():
        if agent["category"] == "assistant":
            return agent
    return None


def _build_system_prompt(agent: Dict[str, Any], extra_context: str = "") -> str:
    name = agent.get("name", "Agente")
    title = agent.get("title", "")
    role = agent.get("role", "")
    body = agent.get("body", "")
    persona_bits = []
    if role:
        persona_bits.append(role)
    if body:
        # aproveita principios/estilo de comunicacao presentes no body
        for section in ["## Communication Style", "## Communication", "## Voice Guidance"]:
            idx = body.find(section)
            if idx != -1:
                chunk = body[idx:idx + 1200]
                persona_bits.append(chunk.strip())
                break
    persona_text = "\n\n".join(persona_bits) if persona_bits else (
        f"Você é {name}, {title}. Aja com profissionalismo, objetividade e precisão."
    )
    extra = f"\n\nCONTEXTO ADICIONAL:\n{extra_context}" if extra_context else ""
    return (
        f"Você é {name} ({title}) — um agente de IA da equipe NEMO IDE.\n\n"
        f"PERSONA:\n{persona_text}{extra}\n\n"
        "DIRETRIZES:\n"
        "- Responda em português do Brasil.\n"
        "- Seja direto e objetivo; profundidade proporcional à complexidade.\n"
        "- Nunca invente fatos, dados ou números; se não souber, diga que não sabe.\n"
        "- Estruture respostas longas com seções claras.\n"
        "- Preserve trabalho existente e nunca exponha credenciais ou dados sensíveis.\n"
    )


def _safe_resolve(path_str: str) -> Path:
    """Resolve e valida um caminho dentro da raiz do projeto."""
    raw = path_str.strip()
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    if str(p) != str(ROOT) and str(ROOT) not in str(p):
        raise HTTPException(status_code=400, detail="Caminho fora do diretório do projeto.")
    return p


def _is_destructive(command: str) -> Optional[str]:
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None


def _run_command(command: str, force: bool = False, timeout: int = 60) -> Dict[str, Any]:
    matched = _is_destructive(command)
    if matched and not force:
        return {
            "ok": False,
            "requires_confirm": True,
            "reason": f"O comando contém uma operação destrutiva ({matched}). Confirme para executar.",
            "stdout": "",
            "stderr": "",
            "code": None,
        }
    safe_timeout = max(1, min(timeout or 60, MAX_TERMINAL_TIMEOUT))
    try:
        if os.name == "nt":
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=safe_timeout, cwd=str(ROOT), errors="replace",
            )
        else:
            proc = subprocess.run(
                shlex.split(command), capture_output=True, text=True,
                timeout=safe_timeout, cwd=str(ROOT), errors="replace",
            )
        return {
            "ok": True,
            "requires_confirm": False,
            "reason": "",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "requires_confirm": False,
            "reason": f"Comando excedeu o tempo limite de {safe_timeout}s.",
            "stdout": "",
            "stderr": "",
            "code": None,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "requires_confirm": False,
            "reason": str(exc),
            "stdout": "",
            "stderr": "",
            "code": None,
        }


def _load_events() -> List[Dict[str, Any]]:
    """Carrega os eventos do calendário a partir do arquivo local (events.json)."""
    if not EVENTS_FILE.is_file():
        return []
    try:
        data = json.loads(EVENTS_FILE.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_events(events: List[Dict[str, Any]]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EVENTS_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Não foi possível persistir eventos: {exc}")


def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    base = {
        "id": "", "title": "", "description": "", "date": "", "time": "09:00",
        "durationMin": 60, "category": "outro", "agentId": "nemo", "remind": 15,
        "createdAt": int(time.time() * 1000),
    }
    base.update({k: v for k, v in event.items() if v is not None and v != ""})
    return base


def _squads_snapshot() -> Dict[str, Any]:
    """Snapshot de squads — replica o formato do plugin squadWatcher do Vite."""
    squads: List[Dict[str, Any]] = []
    active_states: Dict[str, Any] = {}
    if SQUADS_DIR.is_dir():
        for entry in sorted(SQUADS_DIR.iterdir()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name.startswith("_"):
                continue
            yaml_path = entry / "squad.yaml"
            code, name, description, icon, agents = entry.name, entry.name, "", "📋", []
            try:
                import yaml
                if yaml_path.is_file():
                    parsed = yaml.safe_load(yaml_path.read_text(encoding="utf-8", errors="replace"))
                    s = parsed.get("squad") if isinstance(parsed, dict) else None
                    if not isinstance(s, dict):
                        # YAML "flat": os metadados do squad ficam na raiz (opencore style)
                        s = parsed
                    if isinstance(s, dict):
                        code = s.get("code") or code
                        name = s.get("name") or name
                        description = s.get("description") or description
                        icon = s.get("icon") or icon
                        agents = s.get("agents") if isinstance(s.get("agents"), list) else []
                        # fallback: monta agentes a partir de squad-party.csv
                        if not agents:
                            csv_path = entry / "squad-party.csv"
                            if csv_path.is_file():
                                agents = [
                                    line.split(",")[1].strip() if "," in line else line.strip()
                                    for line in csv_path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]
                                    if line.strip() and not line.strip().startswith("#")
                                ]
            except Exception:
                pass
            squads.append({
                "code": code, "name": name, "description": description,
                "icon": icon, "agents": agents,
            })
            state_path = entry / "state.json"
            if state_path.is_file():
                try:
                    active_states[code] = json.loads(state_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
    return {"squads": squads, "activeStates": active_states}


# ---------------------------------------------------------------------------
# Registro do servidor e modelos Pydantic
# ---------------------------------------------------------------------------

app = FastAPI(title=f"{PROJECT_NAME} API", version=VERSION)

# CORS — origens locais por padrão + extras via CORS_ORIGINS (produção/antigravity)
_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8798",
    "http://127.0.0.1:8798",
]
_extra_origins = os.getenv("CORS_ORIGINS", "")
if _extra_origins:
    for _origin in _extra_origins.split(","):
        _origin = _origin.strip()
        if _origin and _origin not in _cors_origins:
            _cors_origins.append(_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client: Optional[OpenRouterClient] = None


def get_client() -> OpenRouterClient:
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    agent: str = "nemo"
    messages: List[ChatMessage] = []
    message: str = ""
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 900
    context: str = ""


class FileSaveRequest(BaseModel):
    path: str
    content: str


class TerminalRequest(BaseModel):
    command: str
    force: bool = False
    timeout: int = 60


class EventRequest(BaseModel):
    id: Optional[str] = None
    title: str = ""
    description: str = ""
    date: str = ""
    time: str = "09:00"
    durationMin: int = 60
    category: str = "outro"
    agentId: str = "nemo"
    remind: int = 15
    createdAt: Optional[int] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/nemo/health")
def health() -> Dict[str, Any]:
    c = get_client()
    return {
        "project": PROJECT_NAME,
        "version": VERSION,
        "time": datetime.now().isoformat(),
        "api_key_configured": c.has_valid_key_format(),
        "models": len(OPENROUTER_MODELS),
        "agents": len(_discover_agents()),
        "squads": len([d for d in SQUADS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]) if SQUADS_DIR.is_dir() else 0,
    }


@app.get("/api/nemo/context")
def context() -> Dict[str, Any]:
    return {
        "project": PROJECT_NAME,
        "root": str(ROOT),
        "agents": _discover_agents(),
        "models": [m.id for m in get_all_models()],
        "squads": [d.name for d in sorted(SQUADS_DIR.iterdir()) if d.is_dir() and not d.name.startswith((".", "_"))] if SQUADS_DIR.is_dir() else [],
        "skills": [d.name for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".", )] if SKILLS_DIR.is_dir() else [],
    }


@app.get("/api/nemo/agents")
def agents() -> List[Dict[str, Any]]:
    return _discover_agents()


# ---------------------------------------------------------------------------
# Calendário — eventos persistidos (JSON em _data/events.json)
# ---------------------------------------------------------------------------

def _gen_event_id() -> str:
    from uuid import uuid4
    return uuid4().hex[:9]


@app.get("/api/nemo/events")
def list_events() -> List[Dict[str, Any]]:
    events = _load_events()
    events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))
    return events


@app.post("/api/nemo/events")
def create_event(req: EventRequest) -> Dict[str, Any]:
    now = int(time.time() * 1000)
    event: Dict[str, Any] = _normalize_event({
        "id": req.id or _gen_event_id(),
        "title": req.title.strip() or "Sem título",
        "description": req.description,
        "date": req.date,
        "time": req.time or "09:00",
        "durationMin": max(5, min(req.durationMin or 60, 1440)),
        "category": req.category or "outro",
        "agentId": req.agentId or "nemo",
        "remind": int(req.remind or 0),
        "createdAt": req.createdAt or now,
    })
    events = _load_events()
    events = [e for e in events if e.get("id") != event["id"]]
    events.append(event)
    _save_events(events)
    return event


@app.put("/api/nemo/events/{event_id}")
def update_event(event_id: str, req: EventRequest) -> Dict[str, Any]:
    events = _load_events()
    for i, e in enumerate(events):
        if e.get("id") == event_id:
            merged = {**e, **{k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}}
            events[i] = _normalize_event(merged)
            _save_events(events)
            return events[i]
    raise HTTPException(status_code=404, detail="Evento não encontrado.")


@app.delete("/api/nemo/events/{event_id}")
def delete_event(event_id: str) -> Dict[str, Any]:
    events = _load_events()
    remaining = [e for e in events if e.get("id") != event_id]
    if len(remaining) == len(events):
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    _save_events(remaining)
    return {"ok": True, "deleted": event_id}


@app.post("/api/nemo/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    agent = _agent_persona(req.agent) or {
        "id": req.agent, "name": "Nemo", "title": "Assistente", "category": "assistant",
        "role": "Assistente pessoal.", "defaultModel": CATEGORY_MODEL_DEFAULT,
    }
    model = req.model or agent.get("defaultModel") or CATEGORY_MODEL_DEFAULT
    fallback_slugs: List[str] = []
    mi = get_model_by_id(model)
    if mi:
        fallback_slugs = [s for s in [model] if False] + mi.fallback_slugs
    system = _build_system_prompt(agent, req.context)
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for m in req.messages[-12:]:
        if m.role in ("user", "assistant") and m.content:
            messages.append({"role": m.role, "content": m.content[:12000]})
    if req.message:
        messages.append({"role": "user", "content": req.message[:12000]})
    if len(messages) == 1:
        messages.append({"role": "user", "content": "Olá."})

    c = get_client()
    started = time.perf_counter()
    if not c.has_valid_key_format():
        return {
            "ok": True,
            "agent": req.agent,
            "content": "⚠️ Minha chave de acesso ao OpenRouter não está configurada. "
                       "Crie um arquivo `.env` a partir de `.env.example` com sua chave do OpenRouter para eu responder de verdade.\n\n"
                       "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro. 🐟",
            "model_used": model,
            "is_fallback": True,
            "offline": True,
            "latency_ms": 0,
        }
    result: CompletionResult = c.chat_completion(
        model=model,
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        fallback_slugs=fallback_slugs or None,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    if result.success:
        return {
            "ok": True,
            "agent": req.agent,
            "content": result.content,
            "model_used": result.model_used,
            "is_fallback": result.is_fallback,
            "latency_ms": latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
        }
    if _is_auth_error(result.error_message or ""):
        # Chave presente mas inválida/expirada → resposta graciosa em PT-BR
        # (o frontend exibe como mensagem normal, marcada como fallback offline).
        return {
            "ok": True,
            "agent": req.agent,
            "content": (
                "⚠️ Minha chave de acesso ao OpenRouter está **invalida ou expirada** "
                "(HTTP 401), então não consigo chamar modelos de IA no momento. 🐟\n\n"
                "Para voltar a responder de verdade:\n"
                "1. Abra o arquivo `.env` do projeto e troque `OPENROUTER_API_KEY` por uma chave nova "
                "(crie em https://openrouter.ai/keys).\n"
                "2. Reinicie o servidor (`python nemo_server.py`).\n\n"
                "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro. "
                "💙 você me deu o diagnóstico?"),
            "model_used": result.model_used or model,
            "is_fallback": True,
            "offline": True,
            "latency_ms": latency_ms,
        }
    return {
        "ok": False,
        "agent": req.agent,
        "error": result.error_message or "Erro desconhecido ao chamar o modelo.",
        "model_used": result.model_used,
        "latency_ms": latency_ms,
    }


def _is_auth_error(message: str) -> bool:
    """Detecta erros de autenticação/credencial do OpenRouter na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "401", "unauthorized", "authentication", "auth", "api key",
        "invalid", "expirad", "expired", "invalid_api_key", "insufficient",
    ]
    return any(m in lowered for m in markers)


@app.get("/api/nemo/files")
def list_files(path: str = Query("", description="Diretório relativo à raiz do projeto")):
    p = _safe_resolve(path)
    if not p.is_dir():
        raise HTTPException(status_code=404, detail="Diretório não encontrado.")
    entries: List[Dict[str, Any]] = []
    for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
        if child.name.startswith((".", "_")) and child.name not in (".env.example",):
            continue
        if child.name == "node_modules":
            continue
        is_dir = child.is_dir()
        rel = child.relative_to(ROOT).as_posix()
        entries.append({
            "name": child.name,
            "path": rel,
            "type": "dir" if is_dir else "file",
            "size": 0 if is_dir else child.stat().st_size,
        })
    return {"path": p.relative_to(ROOT).as_posix() if str(p) != str(ROOT) else "", "entries": entries}


@app.get("/api/nemo/file")
def read_file(path: str = Query(..., description="Caminho relativo")):
    p = _safe_resolve(path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    if p.stat().st_size > 1_500_000:
        raise HTTPException(status_code=413, detail="Arquivo grande demais para exibição.")
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        content = "(arquivo binário)"
    ext = p.suffix.lstrip(".").lower()
    return {"path": p.relative_to(ROOT).as_posix(), "name": p.name, "content": content, "language": ext or "text"}


@app.post("/api/nemo/file/save")
def save_file(req: FileSaveRequest) -> Dict[str, Any]:
    p = _safe_resolve(req.path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(req.content, encoding="utf-8")
        return {"ok": True, "path": p.relative_to(ROOT).as_posix()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Não foi possível salvar: {exc}")


@app.post("/api/nemo/terminal")
def terminal(req: TerminalRequest) -> Dict[str, Any]:
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Comando vazio.")
    return _run_command(req.command, force=req.force, timeout=req.timeout)


@app.get("/api/nemo/models")
def models():
    return [
        {
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "primary_slug": m.primary_slug,
            "description": m.description,
        }
        for m in get_all_models()
    ]


@app.get("/api/nemo/snapshot")
def snapshot() -> Dict[str, Any]:
    return _squads_snapshot()


@app.get("/api/nemo/auth")
def auth() -> Dict[str, Any]:
    """Valida a chave OpenRouter junto ao endpoint oficial /auth/key."""
    return get_client().check_auth()


# ---------------------------------------------------------------------------
# Dashboard compilado (produção): serve o frontend em '/' caso exista dist.
# Registro em nível de módulo para funcionar tanto com `python nemo_server.py`
# quanto com `uvicorn nemo_server:app` (gunicorn/Render/etc).
# ---------------------------------------------------------------------------

def _mount_dashboard() -> None:
    if DASHBOARD_DIST.is_dir() and (DASHBOARD_DIST / "index.html").is_file():
        @app.get("/", include_in_schema=False)
        def serve_index():
            return FileResponse(DASHBOARD_DIST / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str):
            candidate = (DASHBOARD_DIST / full_path).resolve()
            try:
                if full_path and candidate.is_file() and str(candidate).startswith(str(DASHBOARD_DIST.resolve())):
                    return FileResponse(candidate)
            except Exception:
                pass
            return FileResponse(DASHBOARD_DIST / "index.html")


_mount_dashboard()


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="NEMO IDE API Server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-dashboard", action="store_true", help="não tenta servir o build do frontend")
    args = parser.parse_args()

    if args.no_dashboard:
        app.routes[:] = [r for r in app.routes
                         if getattr(r, "path", None) not in ("/", "/{full_path:path}")]

    print(f"🐟 {PROJECT_NAME} API rodando em http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")