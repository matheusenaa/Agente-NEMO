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
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import threading
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
        # resolve() normaliza short names (ex.: MATHEU~1.SIL -> matheus.silva);
        # sem isso a verificacao de containment do _safe_resolve falha no Windows.
        base = Path(sys._MEIPASS).resolve()
        # Fallback robusto: se o pacote de dados não estiver em MEIPASS,
        # procura por agents/ nas proximidades (onedir em outras layouts).
        if not (base / "agents").is_dir():
            for cand in (base.parent, base.parent / "_MEIPASS", Path.cwd()):
                if (cand / "agents").is_dir():
                    base = cand.resolve()
                    break
        return base
    return Path(__file__).resolve().parent

ROOT = _get_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from openrouter_client import OpenRouterClient
from models_config import OPENROUTER_MODELS, get_model_by_id, get_all_models
from auth import AuthError, AuthStore, make_auth_store
from ai_providers import AIProviderService, PROVIDER_META, GEMINI_MODELS, GROQ_MODELS, OPENAI_MODELS
from ai_keys import KeyStore, KeyStoreError, mask_key, looks_like_placeholder
from web_search import WebSearchService, WebSearchError
from data_store import make_data_store

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

AUTH_STORE: AuthStore = make_auth_store(ROOT)

# Camada de IA multirprovedor + busca web + dados (Supabase ou fallback local)
AI_SERVICE = AIProviderService()
KEY_STORE = KeyStore(AUTH_STORE.secret)
WEB_SEARCH_SERVICE = WebSearchService()
DATA_STORE = make_data_store(ROOT, AUTH_STORE.secret)


# Rate limit por usuário (missão §35) — proteção contra consumo ilimitado.
try:
    AI_REQUEST_LIMIT_PER_MINUTE = max(1, int(os.getenv("NEMO_AI_RATE_LIMIT", "30")))
except Exception:
    AI_REQUEST_LIMIT_PER_MINUTE = 30


class _SlidingWindowRateLimit:
    def __init__(self, limit: int):
        self.limit = limit
        self._lock = threading.Lock()
        self._hits: Dict[str, List[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            recent = [t for t in self._hits.get(key, []) if now - t < 60]
            if len(recent) >= self.limit:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True


AI_RATE_LIMITER = _SlidingWindowRateLimit(AI_REQUEST_LIMIT_PER_MINUTE)

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

# Ferramentas permitidas por agente (missão §22/23) — o backend NÃO deixa um
# agente usar ferramenta fora da sua lista.
AGENT_TOOLS: Dict[str, List[str]] = {
    "nemo": ["orquestracao", "agentes", "tasks", "calendario", "search", "memory", "db"],
    "jarvis": ["codigo", "terminal", "tasks", "search", "memory", "db"],
    "analista": ["analise", "db", "memory", "search"],
    "pesquisador": ["web_search", "analise", "memory"],
    "redator": ["conteudo", "memory"],
    "revisor": ["revisao", "memory"],
    "designer": ["imagem", "design", "memory"],
    "criador-video": ["roteiro", "video", "memory"],
    "estrategista": ["estrategia", "memory", "search"],
    "gestor-redes": ["social", "memory"],
    "editor-publicador": ["conteudo", "publicacao", "memory"],
    "seo": ["conteudo", "seo", "search", "memory"],
}

# Sinais de que a pergunta pede informação externa (missão §21: nada de busca
# automática para perguntas simples/conhecimento estável).
SEARCH_HINTS = [
    "preço", "precos", "preco", "notícia", "noticia", "notícias", "noticias",
    "cotação", "cotacao", "dólar", "dolar", "atual", "hoje", "2026", "2025",
    "quanto", "resultado", "vasco", "empresa", "empresas", "quem", "quando",
    "onde", "novo", "novos", "nova", "último", "ultimo", "última", "ultima",
    "jogo", "jogos", "partida", "partidas", "pesquise", "pesquisar", "pesquisa",
    "tabela", "ranking", "elenco", "campeonato", "lançamento", "lancamento",
    "previsão", "previsao", "mercado", "ultrapassa", "tendência", "tendencia",
]

SEARCH_QUERY_ROOTS = re.compile(
    r"^(me (busca|pesquisa|pesquise)|quero (saber|ver|uma pesquisa)|busca|pesquise|procure|investigue)",
    re.IGNORECASE,
)


def _needs_search(message: str, tools: List[str]) -> bool:
    """Missão §21: o agente decide quando buscar na web (e só com permissão)."""
    if not (message or "").strip() or len(message.strip()) < 12:
        return False
    if "web_search" not in tools and "search" not in tools:
        return False
    msg = message.lower()
    if SEARCH_QUERY_ROOTS.search(message):
        return True
    return any(hint in msg for hint in SEARCH_HINTS)


def _search_block(sres: Dict[str, Any]) -> str:
    results = sres.get("results", [])
    lines = [
        "INFORMAÇÕES ENCONTRADAS NA WEB (referência; cite as fontes):",
        f"Mecanismo: {sres.get('provider', '')}",
    ]
    for i, r in enumerate(results[:6], 1):
        lines.append(
            f"{i}. {r.get('title', '') or '(sem título)'}\n   URL: {r.get('url', '')}\n   {r.get('snippet', '')[:320]}"
        )
    lines.append(
        "Separe claramente seu CONHECIMENTO DO MODELO das informações acima. "
        "Não invente fontes nem URLs que não apareceram aqui."
    )
    return "\n".join(lines)


def _memory_block(user_id: str, agent_id: str) -> str:
    """Memória permanente do agente para este usuário (missão §24/25)."""
    try:
        mems = DATA_STORE.list_memories(user_id, agent_id) or []
    except Exception:
        return ""
    if not mems:
        return ""
    lines = ["MEMÓRIAS PERMANENTES SOBRE O USUÁRIO / TAREFAS ANTERIORES (use com contexto):"]
    for m in mems[:6]:
        kind = m.get("kind", "obs")
        lines.append(f"- [{kind}] {str(m.get('content', ''))[:300]}")
    return "\n".join(lines)


def _now_ms() -> int:
    return int(time.time() * 1000)

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


def _coerce_model_for_provider(provider: str, model: str) -> str:
    """Se o modelo resolvido não pertence ao catálogo do provedor escolhido
    (ex.: slug OpenRouter herdado do padrão da categoria), usa o modelo-padrão
    atual do provedor para não chamar com nome inexistente."""
    catalog: Dict[str, List[str]] = {
        "groq": GROQ_MODELS,
        "gemini": GEMINI_MODELS,
        "openai": OPENAI_MODELS,
    }
    known = catalog.get(provider, [])
    if known and model and model not in known and "/" in model:
        return known[0]
    return model


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


def _events_file_for(user_id: str) -> Path:
    """Arquivo de eventos da área privada do usuário (isolamento por usuário)."""
    return AUTH_STORE.events_file(user_id)


def _load_events(file: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Carrega os eventos do calendário a partir do arquivo local (events.json).

    Por padrão usa o arquivo do usuário autenticado (isolamento de dados).
    """
    path = file or EVENTS_FILE
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_events(events: List[Dict[str, Any]], file: Optional[Path] = None) -> None:
    path = file or EVENTS_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
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
    provider: Optional[str] = None
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


class AgentAiOverride(BaseModel):
    """Configuração de IA para um agente específico (missão §40)."""
    provider: Optional[str] = None
    model: Optional[str] = None


class AiSettingsRequest(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    agent_overrides: Optional[Dict[str, AgentAiOverride]] = None


class AiKeyRequest(BaseModel):
    provider: str = ""
    api_key: str = ""
    model: Optional[str] = None


class AiTestRequest(BaseModel):
    provider: str = ""
    api_key: Optional[str] = None
    model: Optional[str] = None


class MemoryRequest(BaseModel):
    agent: str = "nemo"
    content: str = ""
    kind: str = "obs"


class ConversationRequest(BaseModel):
    agent: str = "nemo"
    title: str = ""


class ProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    avatar: Optional[str] = None
    default_agent: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class MessageRequest(BaseModel):
    role: str = "user"
    content: str = ""
    meta: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    id: Optional[str] = None
    title: str = ""
    priority: str = "normal"
    agentId: str = "nemo"
    status: str = "pending"
    dueDate: Optional[int] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/nemo/health")
def health(request: Request) -> Dict[str, Any]:
    c = get_client()
    ai = {
        "providers_configured": [p for p in AI_SERVICE.provider_catalog() if p["configured"]],
        "default_provider": AI_SERVICE.default_provider(),
        "default_model": AI_SERVICE.default_provider_model(),
        "web_search": WEB_SEARCH_SERVICE.available_providers(),
        "store_backend": DATA_STORE.name,
        "encryption": KEY_STORE.available,
    }
    return {
        "project": PROJECT_NAME,
        "version": VERSION,
        "time": datetime.now().isoformat(),
        "api_key_configured": c.has_valid_key_format(),
        "models": len(OPENROUTER_MODELS),
        "agents": len(_discover_agents()),
        "squads": len([d for d in SQUADS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]) if SQUADS_DIR.is_dir() else 0,
        "squad_ws": False,
        "auth": True,
        "ai": ai,
        "authenticated": bool(_current_user(request)),
    }


def _current_user(request: "Request") -> Optional[Dict[str, Any]]:
    """Resolve o usuário autenticado a partir do header Authorization: Bearer <token>."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    return AUTH_STORE.resolve_token(token) if token else None


def _require_user(request: "Request") -> Dict[str, Any]:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação necessária. Faça login.")
    return user


def _require_admin(request: "Request") -> Dict[str, Any]:
    """Só ADMIN acessa arquivos do projeto, terminal e área administrativa."""
    user = _require_user(request)
    if not AUTH_STORE.is_admin(user.get("id", "")):
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador (role 'admin').")
    return user


# ---------------------------------------------------------------------------
# Autenticação / multiusuário
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


class RegisterRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""


@app.post("/api/auth/register")
def register(req: RegisterRequest) -> Dict[str, Any]:
    try:
        user, token = AUTH_STORE.register(req.name, req.email, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    return {"ok": True, "user": user, "token": token}


@app.post("/api/auth/login")
def login(req: LoginRequest) -> Dict[str, Any]:
    try:
        user, token = AUTH_STORE.login(req.email, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    return {"ok": True, "user": user, "token": token}


@app.post("/api/auth/logout")
def logout(request: Request) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        AUTH_STORE.revoke_token(auth[7:].strip())
    return {"ok": True}


@app.get("/api/auth/me")
def me(request: Request) -> Dict[str, Any]:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    return {"ok": True, "user": user}


# ---------------------------------------------------------------------------
# Login social (OAuth 2.0) — Google / Microsoft / Apple
# ---------------------------------------------------------------------------

from oauth import OAuthError, authorize_url, enabled_providers, exchange  # noqa: E402


class OAuthStartResponse(BaseModel):
    provider: str
    url: str
    state: str


@app.get("/api/auth/oauth/status")
def oauth_status() -> Dict[str, Any]:
    """Lista os provedores OAuth habilitados (para a tela de login)."""
    providers = enabled_providers()
    return {"ok": True, "providers": [
        {
            "name": name,
            "enabled": True,
            "label": {
                "google": "Google",
                "microsoft": "Microsoft",
                "apple": "Apple",
            }.get(name, name),
        }
        for name in sorted(providers)
    ]}


@app.get("/api/auth/oauth/{provider}/start")
def oauth_start(provider: str, request: Request) -> Dict[str, Any]:
    """Gera a URL de autorização e o state (assinado) para o provedor."""
    random_part = secrets.token_urlsafe(24)
    # Assina o state para validar no callback (previne CSRF em login social).
    digest = hmac.new(AUTH_STORE.secret, random_part.encode("utf-8"), hashlib.sha256).hexdigest()
    # O provedor devolve apenas `state` — embutimos a assinatura junto.
    state = f"{random_part}.{digest}"
    redirect_uri = f"{_request_base(request)}/api/auth/oauth/{provider}/callback"
    try:
        url = authorize_url(provider, redirect_uri, state)
    except OAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    return {
        "ok": True,
        "provider": provider,
        "url": url,
        "state": state,
    }


@app.get("/api/auth/oauth/{provider}/callback")
def oauth_callback(provider: str, request: Request, code: str = "", state: str = "") -> JSONResponse:
    """Callback do provedor: valida state, troca o code por perfil e loga."""
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização ausente.")
    if "." not in state:
        raise HTTPException(status_code=403, detail="State ausente ou malformado. Tente novamente.")
    random_part, _, sig = state.rpartition(".")
    expected = hmac.new(AUTH_STORE.secret, random_part.encode("utf-8"), hashlib.sha256).hexdigest()
    if not random_part or not hmac.compare_digest(expected, sig or ""):
        raise HTTPException(status_code=403, detail="State inválido ou expirado. Tente novamente.")
    redirect_uri = f"{_request_base(request)}/api/auth/oauth/{provider}/callback"
    try:
        account = exchange(provider, code, redirect_uri)
        user, token = AUTH_STORE.oauth_login(
            provider,
            account.get("provider_id", ""),
            account.get("email", ""),
            account.get("name", ""),
        )
    except OAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)

    # Conclui no frontend: redireciona com token+user (hash) para /auth#oauth=1.
    payload = base64.urlsafe_b64encode(
        json.dumps({"token": token, "user": user}).encode("utf-8")
    ).rstrip(b"=").decode()
    url = f"/#oauth={payload}"
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0;url={url}'></head>"
        "<body><p>Login concluído — redirecionando…</p></body></html>"
    ).format(url=url)
    return HTMLResponse(html, status_code=200)


def _request_base(request: Request) -> str:
    """Base pública do request (schema://host) para montar redirect_uris."""
    forwarded = request.headers.get("x-forwarded-proto", "")
    scheme = forwarded.split(",")[0].strip() or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.url.netloc
    return f"{scheme}://{host}"


# ---------------------------------------------------------------------------
# Gestão de usuários / permissões (somente ADMIN)
# ---------------------------------------------------------------------------

class RoleRequest(BaseModel):
    userId: str = ""
    role: str = ""


@app.get("/api/admin/users")
def admin_list_users(request: Request) -> Dict[str, Any]:
    _require_admin(request)
    return {"ok": True, "users": AUTH_STORE.list_users()}


@app.put("/api/admin/users/role")
def admin_set_role(req: RoleRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
    if not req.userId:
        raise HTTPException(status_code=400, detail="Informe userId.")
    if req.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role inválida. Use 'user' ou 'admin'.")
    user = AUTH_STORE.set_role(req.userId, req.role)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"ok": True, "user": user}


# ---------------------------------------------------------------------------
# Calendário — eventos persistidos por usuário (JSON em _data/users/<id>/events.json)
# ---------------------------------------------------------------------------


@app.get("/api/nemo/context")
def context(request: Request) -> Dict[str, Any]:
    _require_user(request)
    return {
        "project": PROJECT_NAME,
        "root": str(ROOT),
        "agents": _discover_agents(),
        "models": [m.id for m in get_all_models()],
        "squads": [d.name for d in sorted(SQUADS_DIR.iterdir()) if d.is_dir() and not d.name.startswith((".", "_"))] if SQUADS_DIR.is_dir() else [],
        "skills": [d.name for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".", )] if SKILLS_DIR.is_dir() else [],
    }


@app.get("/api/nemo/agents")
def agents(request: Request) -> List[Dict[str, Any]]:
    _require_user(request)
    return _discover_agents()


# ---------------------------------------------------------------------------
# Calendário — eventos persistidos (JSON em _data/events.json)
# ---------------------------------------------------------------------------

def _gen_event_id() -> str:
    from uuid import uuid4
    return uuid4().hex[:9]


@app.get("/api/nemo/events")
def list_events(request: Request) -> List[Dict[str, Any]]:
    user = _require_user(request)
    events = _load_events(_events_file_for(user["id"]))
    events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))
    return events


@app.post("/api/nemo/events")
def create_event(req: EventRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
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
    file = _events_file_for(user["id"])
    events = _load_events(file)
    events = [e for e in events if e.get("id") != event["id"]]
    events.append(event)
    _save_events(events, file)
    return event


@app.put("/api/nemo/events/{event_id}")
def update_event(event_id: str, req: EventRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    file = _events_file_for(user["id"])
    events = _load_events(file)
    for i, e in enumerate(events):
        if e.get("id") == event_id:
            merged = {**e, **{k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}}
            events[i] = _normalize_event(merged)
            _save_events(events, file)
            return events[i]
    raise HTTPException(status_code=404, detail="Evento não encontrado.")


@app.delete("/api/nemo/events/{event_id}")
def delete_event(event_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    file = _events_file_for(user["id"])
    events = _load_events(file)
    remaining = [e for e in events if e.get("id") != event_id]
    if len(remaining) == len(events):
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    _save_events(remaining, file)
    return {"ok": True, "deleted": event_id}


@app.post("/api/nemo/chat")
def chat(req: ChatRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not AI_RATE_LIMITER.allow(user["id"]):
        return {
            "ok": True,
            "agent": req.agent,
            "content": (
                f"⏳ Você atingiu o limite de **{AI_REQUEST_LIMIT_PER_MINUTE}** requisições de IA "
                "por minuto. Aguarde um instante e tente de novo.\n\n"
                "O limite é ajustável em `.env` → `NEMO_AI_RATE_LIMIT`."),
            "offline": True,
            "rate_limited": True,
            "latency_ms": 0,
        }
    agent = _agent_persona(req.agent) or {
        "id": req.agent, "name": "Nemo", "title": "Assistente", "category": "assistant",
        "role": "Assistente pessoal.", "defaultModel": CATEGORY_MODEL_DEFAULT,
    }

    # --- Resolução de provedor/modelo (requisição > agente > usuário > sistema) --
    settings: Dict[str, Any] = {}
    try:
        settings = DATA_STORE.get_ai_settings(user["id"]) or {}
    except Exception:
        settings = {}
    agent_override: Dict[str, Any] = (settings.get("agent_overrides") or {}).get(req.agent) or {}
    provider = (req.provider
                or agent_override.get("provider")
                or settings.get("default_provider")
                or AI_SERVICE.default_provider() or "openrouter")
    model = (req.model
             or agent_override.get("model")
             or settings.get("default_model")
             or agent.get("defaultModel") or CATEGORY_MODEL_DEFAULT)
    model = _coerce_model_for_provider(provider, model)

    # --- Ferramentas (missão §22/23) e busca condicional (missão §21) --------
    tools = AGENT_TOOLS.get(agent["id"], [])
    search_extra = ""
    if req.message and _needs_search(req.message, tools):
        try:
            sres = WEB_SEARCH_SERVICE.search(user["id"], req.message.strip()[:200], 5)
            if sres.get("ok"):
                search_extra = _search_block(sres)
                try:
                    DATA_STORE.save_search(user["id"], agent["id"], req.message, sres.get("provider", ""), sres.get("results", []))
                except Exception:
                    pass
        except WebSearchError:
            pass
        except Exception:
            pass

    memory_extra = _memory_block(user["id"], agent["id"])

    extras = [b for b in (req.context, memory_extra, search_extra) if b]
    system = _build_system_prompt(agent, "\n\n".join(extras))

    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    for m in req.messages[-12:]:
        if m.role in ("user", "assistant") and m.content:
            messages.append({"role": m.role, "content": m.content[:12000]})
    if req.message:
        messages.append({"role": "user", "content": req.message[:12000]})
    if len(messages) == 1:
        messages.append({"role": "user", "content": "Olá."})

    configured_ids = [p["id"] for p in AI_SERVICE.provider_catalog() if p["configured"]]
    user_key_providers: set = set()
    try:
        user_key_providers = {k.get("provider") for k in (DATA_STORE.list_api_keys(user["id"]) or [])}
    except Exception:
        user_key_providers = set()

    api_key = None
    if provider not in configured_ids:
        try:
            api_key = DATA_STORE.get_api_key(user["id"], provider)
        except Exception:
            api_key = None
    if not AI_SERVICE.has_system_key(provider) and not api_key:
        # Nenhuma chave para o provedor escolhido → tenta degradar graciosamente
        # para qualquer provedor realmente configurado (missão §62).
        if configured_ids:
            provider = configured_ids[0]
        elif user_key_providers:
            provider = sorted(user_key_providers)[0]
            try:
                api_key = DATA_STORE.get_api_key(user["id"], provider)
            except Exception:
                api_key = None
        else:
            return _offline_no_provider(provider, req.agent, model)

    fallback_chain = [p for p in configured_ids if p != provider][:2]
    fallback_slugs: List[str] = []
    mi = get_model_by_id(model)
    if mi:
        fallback_slugs = mi.fallback_slugs

    c = get_client()
    started = time.perf_counter()
    result = AI_SERVICE.complete(
        provider=provider,
        model=model,
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        api_key=api_key,
        fallback_providers=fallback_chain,
        fallback_slugs=fallback_slugs,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    model_used = result.model_used or model

    if result.success:
        _persist_chat(user["id"], agent["id"], req.message, result.content)
        _log_activity(user["id"], agent["id"], "chat", "ok", result.provider, result.model_used, result.latency_ms,
                      result.prompt_tokens, result.completion_tokens, result.total_tokens)
        return {
            "ok": True,
            "agent": req.agent,
            "content": result.content,
            "model_used": result.model_used,
            "provider": result.provider,
            "is_fallback": result.is_fallback,
            "latency_ms": latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
        }
    _log_activity(user["id"], agent["id"], "chat", "error", result.provider, result.model_used, latency_ms,
                  result.prompt_tokens, result.completion_tokens, result.total_tokens)
    if _is_auth_error(result.error_message or ""):
        # Chave presente mas inválida/expirada → resposta graciosa (PT-BR),
        # sem expor o erro técnico ao usuário.
        return {
            "ok": True,
            "agent": req.agent,
            "content": (
                f"⚠️ A chave do **{_provider_name(result.provider)}** está inválida ou expirada, "
                "então não consigo chamar modelos de IA no momento. 🐟\n\n"
                "Para voltar a responder de verdade:\n"
                "1. Vá em **Configurações → Inteligência Artificial** e atualize a chave, ou\n"
                "2. Ajuste as credenciais no `.env` do projeto e reinicie o servidor.\n\n"
                "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro."),
            "model_used": model_used,
            "provider": result.provider,
            "is_fallback": True,
            "offline": True,
            "latency_ms": latency_ms,
        }
    if _is_connection_error(result.error_message or ""):
        return {
            "ok": True,
            "agent": req.agent,
            "content": (
                f"⚠️ Não consegui acessar o **{_provider_name(result.provider)}** agora "
                "(rede indisponível ou bloqueada), então não consigo chamar modelos de IA no momento. 🐟\n\n"
                "Para voltar a responder de verdade:\n"
                "1. Verifique sua conexão com a internet (e se a rede/firewall permite o provedor).\n"
                "2. Confirme que a chave está válida nas Configurações de IA e tente novamente.\n\n"
                "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro."),
            "model_used": model_used,
            "provider": result.provider,
            "is_fallback": True,
            "offline": True,
            "latency_ms": latency_ms,
        }
    return {
        "ok": False,
        "agent": req.agent,
        "error": f"Não foi possível utilizar o {_provider_name(result.provider)} neste momento.",
        "provider": result.provider,
        "model_used": model_used,
        "latency_ms": latency_ms,
    }


def _provider_name(provider: str) -> str:
    return PROVIDER_META.get(provider or "", PROVIDER_META["openrouter"])["name"]


def _offline_no_provider(provider: str, agent_id: str, model: str) -> Dict[str, Any]:
    """Resposta graciosa quando nenhum provedor está configurado (missão §45/62)."""
    _log_activity("?", agent_id, "chat", "no_provider", provider, model)
    return {
        "ok": True,
        "agent": agent_id,
        "content": (
            "⚠️ Nenhum provedor de IA está configurado no momento, então não posso "
            "responder de verdade. 🐟\n\n"
            "Para ativar, configure pelo menos um deles:\n"
            "- **Gemini** (https://aistudio.google.com) → `GEMINI_API_KEY` no `.env`\n"
            "- **Groq** (https://console.groq.com) → `GROQ_API_KEY` no `.env`\n"
            "- **OpenRouter** (https://openrouter.ai/keys) → `OPENROUTER_API_KEY` no `.env`\n\n"
            "E em **Configurações → Inteligência Artificial** você pode usar sua própria chave.\n\n"
            "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro."),
        "model_used": model,
        "provider": provider,
        "is_fallback": True,
        "offline": True,
        "latency_ms": 0,
    }


def _persist_chat(user_id: str, agent_id: str, user_message: str, reply: str) -> None:
    """Persiste a conversa (Supabase ou local) — nunca quebra o chat."""
    try:
        convs = DATA_STORE.list_conversations(user_id, agent_id) or []
        conv = convs[0] if convs else DATA_STORE.create_conversation(user_id, agent_id, (user_message or "")[:60])
        if user_message:
            DATA_STORE.append_message(user_id, conv["id"], "user", user_message[:12000], {})
        if reply:
            DATA_STORE.append_message(user_id, conv["id"], "assistant", reply[:20000], {})
    except Exception:
        pass


def _log_activity(user_id: str, agent_id: str, operation: str, status: str,
                  provider: str = "", model: str = "", latency: float = 0.0,
                  prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None:
    try:
        DATA_STORE.log_activity(user_id, agent_id, operation, status, provider, model, latency,
                                prompt_tokens, completion_tokens, total_tokens)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Central de IA: config, chaves dos usuários, testes, busca, memória, conversas
# ---------------------------------------------------------------------------


@app.get("/api/nemo/ai/config")
def ai_config(request: Request) -> Dict[str, Any]:
    """Central de IA (missão §39/45): provedores do sistema + configuração e
    chaves MASCARADAS do usuário. Nunca expõe a chave completa."""
    user = _require_user(request)
    settings: Dict[str, Any] = {}
    keys: List[Dict[str, Any]] = []
    try:
        settings = DATA_STORE.get_ai_settings(user["id"]) or {}
        keys = DATA_STORE.list_api_keys(user["id"]) or []
    except Exception:
        pass
    return {
        "ok": True,
        "system": {
            "providers": AI_SERVICE.provider_catalog(),
            "default_provider": AI_SERVICE.default_provider(),
            "web_search": WEB_SEARCH_SERVICE.available_providers(),
            "store_backend": DATA_STORE.name,
            "encryption": KEY_STORE.available,
        },
        "user": {"settings": settings, "keys": keys},
    }


@app.post("/api/nemo/ai/config")
def ai_save_config(req: AiSettingsRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if req.default_provider and req.default_provider not in PROVIDER_META:
        raise HTTPException(status_code=400, detail="Provedor de IA desconhecido.")
    payload: Dict[str, Any] = {
        "default_provider": req.default_provider,
        "default_model": req.default_model,
    }
    if req.agent_overrides is not None:
        # Mescla (não destrói) os overrides já salvos de outros agentes.
        merged: Dict[str, Dict[str, Any]] = {}
        try:
            merged = dict((DATA_STORE.get_ai_settings(user["id"]) or {}).get("agent_overrides") or {})
        except Exception:
            merged = {}
        for agent_id, spec in req.agent_overrides.items():
            vals = {k: v for k, v in spec.model_dump().items() if v is not None}
            if not vals:
                merged.pop(agent_id, None)
                continue
            cur = dict(merged.get(agent_id) or {})
            cur.update(vals)
            merged[agent_id] = cur
        payload["agent_overrides"] = merged
    DATA_STORE.save_ai_settings(user["id"], payload)
    _log_activity(user["id"], "nemo", "ai_config", "ok", req.default_provider or "", req.default_model or "")
    return {"ok": True}


@app.post("/api/nemo/ai/keys")
def ai_save_key(req: AiKeyRequest, request: Request) -> Dict[str, Any]:
    """Salva a chave do usuário JÁ CRIPTOGRAFADA (missão §16-18). Testa a
    conexão e devolve somente a máscara."""
    user = _require_user(request)
    provider = (req.provider or "").strip().lower()
    if provider not in PROVIDER_META:
        raise HTTPException(status_code=400, detail="Provedor de IA desconhecido.")
    if not req.api_key or looks_like_placeholder(req.api_key):
        raise HTTPException(status_code=400, detail="Informe uma chave válida.")
    test = AI_SERVICE.test_key(provider, req.api_key, req.model)
    try:
        encrypted = KEY_STORE.encrypt(req.api_key)
    except KeyStoreError as exc:
        raise HTTPException(status_code=500, detail=exc.message)
    DATA_STORE.save_api_key(
        user["id"], provider, encrypted, mask_key(req.api_key),
        model=req.model or "", verified=bool(test.get("ok")),
    )
    _log_activity(user["id"], "nemo", "save_key", "ok" if test.get("ok") else "auth_error", provider, req.model or "")
    return {"ok": True, "masked": mask_key(req.api_key), "verified": bool(test.get("ok")), "test": test}


@app.delete("/api/nemo/ai/keys/{provider}")
def ai_delete_key(provider: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    try:
        ok = DATA_STORE.delete_api_key(user["id"], provider)
    except Exception:
        ok = False
    _log_activity(user["id"], "nemo", "delete_key", "ok" if ok else "not_found", provider)
    return {"ok": ok, "deleted": provider}


@app.post("/api/nemo/ai/test")
def ai_test(req: AiTestRequest, request: Request) -> Dict[str, Any]:
    """Testa conexão com a chave informada OU a armazenada/do sistema. Nunca
    exibe a chave no resultado (missão §19)."""
    user = _require_user(request)
    provider = (req.provider or "").strip().lower()
    if provider not in PROVIDER_META:
        raise HTTPException(status_code=400, detail="Provedor de IA desconhecido.")
    api_key: Optional[str] = req.api_key
    if not api_key:
        try:
            api_key = DATA_STORE.get_api_key(user["id"], provider) or None
        except Exception:
            api_key = None
        if not api_key and not AI_SERVICE.has_system_key(provider):
            return {"ok": False, "provider": provider, "message": "Nenhuma chave configurada para este provedor."}
    try:
        return AI_SERVICE.test_key(provider, api_key or "", req.model)
    except Exception as exc:
        return {"ok": False, "provider": provider, "message": "Não foi possível autenticar.", "detail": str(exc)[:120]}


@app.get("/api/nemo/ai/search")
def ai_search(request: Request, query: str = Query("", description="Termo de busca"),
              limit: int = 6, agent: str = "pesquisador") -> Dict[str, Any]:
    user = _require_user(request)
    try:
        res = WEB_SEARCH_SERVICE.search(user["id"], query, limit)
        if res.get("ok"):
            try:
                DATA_STORE.save_search(user["id"], agent, query, res.get("provider", ""), res.get("results", []))
            except Exception:
                pass
            _log_activity(user["id"], agent, "web_search", "ok", res.get("provider", ""))
        return res
    except WebSearchError as exc:
        return {"ok": False, "query": query, "results": [], "error": exc.message}


@app.get("/api/nemo/ai/memories")
def ai_memories(request: Request, agent: str = "") -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "memories": DATA_STORE.list_memories(user["id"], agent or None)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/nemo/ai/memories")
def ai_save_memory(req: MemoryRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not (req.content or "").strip():
        raise HTTPException(status_code=400, detail="Memória vazia.")
    mem = DATA_STORE.save_memory(user["id"], req.agent or "nemo", req.content.strip()[:2000], req.kind or "obs")
    _log_activity(user["id"], req.agent or "nemo", "memory_save", "ok")
    return {"ok": True, "memory": mem}


@app.delete("/api/nemo/ai/memories/{memory_id}")
def ai_delete_memory(memory_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    ok = DATA_STORE.delete_memory(user["id"], memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memória não encontrada.")
    return {"ok": True, "deleted": memory_id}


@app.get("/api/nemo/ai/activity")
def ai_activity(request: Request, limit: int = 50) -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "activity": DATA_STORE.list_activity(user["id"], int(limit) or 50)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Conversas persistidas (Supabase ou local) — missão §26
# ---------------------------------------------------------------------------


@app.get("/api/nemo/conversations")
def conversations_list(request: Request, agent: str = "", q: str = "") -> Dict[str, Any]:
    user = _require_user(request)
    try:
        convs = DATA_STORE.list_conversations(user["id"], agent or None)
        needle = q.strip().lower()
        if needle:
            found = []
            for c in convs:
                hay = (c.get("title") or "").lower()
                if needle in hay:
                    found.append(c)
                    continue
                try:
                    for m in DATA_STORE.list_messages(user["id"], c["id"]):
                        if needle in (m.get("content") or "").lower():
                            found.append(c)
                            break
                except Exception:
                    continue
            convs = found
        return {"ok": True, "conversations": convs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/nemo/conversations")
def conversations_create(req: ConversationRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    conv = DATA_STORE.create_conversation(user["id"], req.agent or "nemo", req.title)
    return {"ok": True, "conversation": conv}


@app.delete("/api/nemo/conversations/{conversation_id}")
def conversations_delete(conversation_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    deleted = DATA_STORE.delete_conversation(user["id"], conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return {"ok": True, "deleted": conversation_id}


@app.get("/api/nemo/conversations/{conversation_id}/messages")
def conversations_messages(conversation_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "messages": DATA_STORE.list_messages(user["id"], conversation_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/nemo/profile")
def profile_get(request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    profile = DATA_STORE.get_profile(user["id"]) or {}
    base = {"id": user["id"], "email": user.get("email", ""), "name": user.get("name", "")}
    base.update({k: v for k, v in profile.items() if k in ("name", "email", "language", "avatar", "default_agent", "preferences")})
    return {"ok": True, "profile": base}


@app.post("/api/nemo/profile")
def profile_save(req: ProfileRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    data = {k: v for k, v in req.model_dump(exclude_none=True).items() if v is not None and v != ""}
    data.setdefault("email", user.get("email", ""))
    DATA_STORE.save_profile(user["id"], data)
    return {"ok": True, "profile": {**data, "id": user["id"]}}


# ---------------------------------------------------------------------------
# Tarefas persistidas (Supabase ou local) — missão §28 (estados da TASK)
# ---------------------------------------------------------------------------

VALID_TASK_STATUS = ("pending", "running", "done", "error", "cancelled")


@app.get("/api/nemo/tasks")
def tasks_list(request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "tasks": DATA_STORE.list_tasks(user["id"])}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/nemo/tasks")
def tasks_save(req: TaskRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    task = {
        "id": req.id or _gen_event_id(),
        "title": (req.title or "").strip() or "Tarefa sem título",
        "priority": req.priority if req.priority in ("urgente", "importante", "normal", "baixa") else "normal",
        "agent_id": req.agentId or "nemo",
        "status": req.status if req.status in VALID_TASK_STATUS else "pending",
        "created_at": _now_ms(),
        "due_date": req.dueDate,
        "done_at": _now_ms() if req.status == "done" else None,
    }
    DATA_STORE.save_task(user["id"], task)
    return {"ok": True, "task": task}


@app.delete("/api/nemo/tasks/{task_id}")
def tasks_delete(task_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    ok = DATA_STORE.delete_task(user["id"], task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"ok": True, "deleted": task_id}


def _is_auth_error(message: str) -> bool:
    """Detecta erros de autentica��o/credencial do OpenRouter na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "401", "unauthorized", "authentication", "auth", "api key",
        "invalid", "expirad", "expired", "invalid_api_key", "insufficient",
    ]
    return any(m in lowered for m in markers)


def _is_connection_error(message: str) -> bool:
    """Detecta falhas de rede (sem internet/OpenRouter inacessível/timeouts) na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "apiconnectionerror", "connection error", "connectionerror",
        "connection reset", "reseterror", "reset", "timeout", "timed out",
        "dns", "max retries", "cannot connect", "network", "connection aborted",
        "unreachable", "ssl", "tls", "failed to resolve",
    ]
    return any(m in lowered for m in markers)


@app.get("/api/nemo/files")
def list_files(request: Request, path: str = Query("", description="Diretório relativo à raiz do projeto")):
    _require_admin(request)
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
def read_file(request: Request, path: str = Query(..., description="Caminho relativo")):
    _require_admin(request)
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
def save_file(req: FileSaveRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
    p = _safe_resolve(req.path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(req.content, encoding="utf-8")
        return {"ok": True, "path": p.relative_to(ROOT).as_posix()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Não foi possível salvar: {exc}")


@app.post("/api/nemo/terminal")
def terminal(req: TerminalRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
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
def snapshot(request: Request) -> Dict[str, Any]:
    _require_user(request)
    return _squads_snapshot()


@app.get("/api/nemo/auth")
def auth(request: Request) -> Dict[str, Any]:
    """Valida a chave OpenRouter junto ao endpoint oficial /auth/key (admin)."""
    _require_admin(request)
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