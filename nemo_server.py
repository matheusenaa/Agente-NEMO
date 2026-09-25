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
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

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

from fastapi import Body, FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from openrouter_client import OpenRouterClient, CompletionResult
from models_config import OPENROUTER_MODELS, get_model_by_id, get_all_models
from auth import AuthError, AuthStore, make_auth_store

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
SENSITIVE_PATH_PARTS = {".git", "_data", "node_modules", "__pycache__"}
SENSITIVE_FILE_NAMES = {
    ".env", "auth_secret", "sessions.json", "users.json", "oauth_states.json",
    "id_rsa", "id_ed25519",
}
SENSITIVE_FILE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".p8"}

AUTH_STORE: AuthStore = make_auth_store(ROOT)
SESSION_COOKIE_NAME = "nemo_session"
OAUTH_STATE_COOKIE_NAME = "nemo_oauth_state"

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
            "body": meta.get("body", ""),
            "version": meta.get("version", "1.0.0"),
            "file": path.relative_to(ROOT).as_posix(),
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
    try:
        p.relative_to(ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho fora do diretório do projeto.")
    return p


def _is_sensitive_path(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return True
    if any(part in SENSITIVE_PATH_PARTS for part in relative.parts):
        return True
    if relative.name in SENSITIVE_FILE_NAMES:
        return True
    if relative.name.startswith(".") and relative.name != ".env.example":
        return True
    return relative.suffix.lower() in SENSITIVE_FILE_SUFFIXES


def _is_destructive(command: str) -> Optional[str]:
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None


def _contains_sensitive_path(command: str) -> bool:
    lowered = command.casefold()
    markers = (
        ".env", "auth_secret", "sessions.json", "users.json", "oauth_states.json",
        ".git/", ".git\\", "id_rsa", "id_ed25519", ".p8", ".pem", ".key",
    )
    return any(marker in lowered for marker in markers)


def _run_command(command: str, force: bool = False, timeout: int = 60) -> Dict[str, Any]:
    if _contains_sensitive_path(command):
        return {
            "ok": False,
            "requires_confirm": False,
            "reason": "O comando referencia um caminho sensível bloqueado.",
            "stdout": "",
            "stderr": "",
            "code": None,
        }
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


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith("/api/"):
        if not request.url.path.startswith("/api/auth/oauth/") or not request.url.path.endswith("/callback"):
            origin = request.headers.get("origin", "").rstrip("/")
            fetch_site = request.headers.get("sec-fetch-site", "").lower()
            request_origin = _request_base(request).rstrip("/")
            if origin and origin not in _cors_origins and origin != request_origin:
                return JSONResponse({"detail": "Origem da requisição não permitida."}, status_code=403)
            if not origin and fetch_site == "cross-site":
                return JSONResponse({"detail": "Origem da requisição não permitida."}, status_code=403)
    return await call_next(request)


_client: Optional[OpenRouterClient] = None


def get_client() -> OpenRouterClient:
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=12000)


class ChatRequest(BaseModel):
    agent: str = Field(default="nemo", min_length=1, max_length=100)
    messages: List[ChatMessage] = Field(default_factory=list, max_length=20)
    message: str = Field(default="", max_length=12000)
    model: Optional[str] = Field(default=None, max_length=200)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=900, ge=1, le=4000)
    context: str = Field(default="", max_length=12000)


class FileSaveRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2_000_000)


class TerminalRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    force: bool = False
    timeout: int = Field(default=60, ge=1, le=120)


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
def health(request: Request) -> Dict[str, Any]:
    c = get_client()
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
        "authenticated": bool(_current_user(request)),
    }


def _session_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return request.cookies.get(SESSION_COOKIE_NAME) or None


def _secure_cookie(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded_proto == "https" or request.url.scheme == "https"


def _set_session_cookie(response: Response, request: Request, token: str, remember: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=AuthStore.session_max_age(remember),
        httponly=True,
        secure=_secure_cookie(request),
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="lax",
        path="/",
    )


def _current_user(request: "Request") -> Optional[Dict[str, Any]]:
    token = _session_token(request)
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
    remember: bool = True


class RegisterRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    remember: bool = True


@app.post("/api/auth/register")
def register(req: RegisterRequest, request: Request, response: Response) -> Dict[str, Any]:
    try:
        user, token = AUTH_STORE.register(req.name, req.email, req.password, req.remember)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    _set_session_cookie(response, request, token, req.remember)
    return {"ok": True, "user": user}


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request, response: Response) -> Dict[str, Any]:
    try:
        user, token = AUTH_STORE.login(req.email, req.password, req.remember)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    _set_session_cookie(response, request, token, req.remember)
    return {"ok": True, "user": user}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> Dict[str, Any]:
    token = _session_token(request)
    if token:
        AUTH_STORE.revoke_token(token)
    _clear_session_cookie(response, request)
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
def oauth_start(provider: str, request: Request, response: Response) -> Dict[str, Any]:
    if provider not in ("google", "microsoft", "apple"):
        raise HTTPException(status_code=400, detail="Provedor OAuth desconhecido.")
    state, nonce = AUTH_STORE.create_oauth_state(provider)
    redirect_uri = f"{_request_base(request)}/api/auth/oauth/{provider}/callback"
    try:
        url = authorize_url(provider, redirect_uri, state, nonce)
    except OAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        nonce,
        max_age=600,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="none" if provider == "apple" and _secure_cookie(request) else "lax",
        path="/",
    )
    return {
        "ok": True,
        "provider": provider,
        "url": url,
        "state": state,
    }


def _complete_oauth(provider: str, request: Request, response: Response, code: str, state: str) -> HTMLResponse:
    if len(code) > 4096 or len(state) > 512:
        raise HTTPException(status_code=400, detail="Parâmetros OAuth inválidos.")
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização ausente.")
    nonce = state.rpartition(".")[0]
    browser_nonce = request.cookies.get(OAUTH_STATE_COOKIE_NAME, "")
    if not nonce or not browser_nonce or not hmac.compare_digest(browser_nonce, nonce):
        raise HTTPException(status_code=403, detail="State inválido, expirado ou associado a outro navegador.")
    record = AUTH_STORE.consume_oauth_state(state, provider)
    if not record:
        raise HTTPException(status_code=403, detail="State inválido, expirado ou já utilizado.")
    redirect_uri = f"{_request_base(request)}/api/auth/oauth/{provider}/callback"
    try:
        account = exchange(provider, code, redirect_uri, nonce)
        user, token = AUTH_STORE.oauth_login(
            provider,
            account.get("provider_id", ""),
            account.get("email", ""),
            account.get("name", ""),
            account.get("email_verified") is True,
        )
    except OAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    _set_session_cookie(response, request, token, True)
    response.delete_cookie(
        OAUTH_STATE_COOKIE_NAME,
        httponly=True,
        secure=_secure_cookie(request),
        samesite="lax",
        path="/",
    )
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='0;url=/#oauth=success'></head>"
        "<body><p>Login concluído — redirecionando…</p></body></html>"
    )
    result = HTMLResponse(html, status_code=200)
    for key, value in response.raw_headers:
        if key.lower() == b"set-cookie":
            result.raw_headers.append((key, value))
    return result


@app.get("/api/auth/oauth/{provider}/callback")
def oauth_callback(provider: str, request: Request, response: Response, code: str = "", state: str = "") -> HTMLResponse:
    return _complete_oauth(provider, request, response, code, state)


@app.post("/api/auth/oauth/{provider}/callback")
def oauth_callback_post(
    provider: str,
    request: Request,
    response: Response,
    code: str = Form(""),
    state: str = Form(""),
) -> HTMLResponse:
    return _complete_oauth(provider, request, response, code, state)


def _request_base(request: Request) -> str:
    configured_base = os.getenv("OAUTH_REDIRECT_BASE", "").strip().rstrip("/")
    if configured_base:
        return configured_base
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
    return {
        "ok": True,
        "users": AUTH_STORE.list_users(),
        "duplicate_emails": AUTH_STORE.duplicate_emails(),
    }


@app.put("/api/admin/users/role")
def admin_set_role(req: RoleRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
    if not req.userId:
        raise HTTPException(status_code=400, detail="Informe userId.")
    if req.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role inválida. Use 'user' ou 'admin'.")
    try:
        user = AUTH_STORE.set_role(req.userId, req.role)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
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
    _require_user(request)
    agent = _agent_persona(req.agent) or {
        "id": req.agent, "name": "Nemo", "title": "Assistente", "category": "assistant",
        "role": "Assistente pessoal.", "defaultModel": CATEGORY_MODEL_DEFAULT,
    }
    model = req.model or agent.get("defaultModel") or CATEGORY_MODEL_DEFAULT
    mi = get_model_by_id(model)
    if mi is None:
        raise HTTPException(status_code=400, detail="Modelo não configurado para o NEMO.")
    fallback_slugs = list(mi.fallback_slugs)
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
            "ok": False,
            "agent": req.agent,
            "content": "⚠️ Minha chave de acesso ao OpenRouter não está configurada. Crie um arquivo `.env` a partir de `.env.example` com sua chave do OpenRouter para eu responder de verdade.\n\nEnquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro. 🐟",
            "error": "OPENROUTER_API_KEY não configurada.",
            "error_code": "missing_key",
            "model_used": model,
            "is_fallback": False,
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
            "finish_reason": result.finish_reason,
        }
    if _is_auth_error(result.error_message or ""):
        return {
            "ok": False,
            "agent": req.agent,
            "content": (
                "⚠️ Minha chave de acesso ao OpenRouter está inválida ou expirada (HTTP 401), então não consigo chamar modelos de IA no momento. 🐟\n\n"
                "Para voltar a responder de verdade:\n"
                "1. Troque `OPENROUTER_API_KEY` no arquivo `.env` por uma chave válida.\n"
                "2. Reinicie o servidor.\n\n"
                "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro."),
            "error": "Credencial do OpenRouter inválida ou expirada.",
            "error_code": "openrouter_auth",
            "model_used": result.model_used or model,
            "is_fallback": False,
            "offline": True,
            "latency_ms": latency_ms,
        }
    if _is_connection_error(result.error_message or ""):
        return {
            "ok": False,
            "agent": req.agent,
            "content": (
                "⚠️ Não consegui acessar o OpenRouter agora (rede indisponível ou bloqueada), então não consigo chamar modelos de IA no momento. 🐟\n\n"
                "Verifique sua conexão com a internet e o acesso a `openrouter.ai`, confirme a chave no `.env` e reinicie o servidor.\n\n"
                "Enquanto isso, posso listar arquivos, montar tarefas e preparar o roteiro."),
            "error": "OpenRouter temporariamente inacessível.",
            "error_code": "openrouter_unavailable",
            "model_used": result.model_used or model,
            "is_fallback": False,
            "offline": True,
            "latency_ms": latency_ms,
        }
    return {
        "ok": False,
        "agent": req.agent,
        "content": "Não consegui concluir a solicitação no modelo selecionado.",
        "error": "Erro ao chamar o modelo selecionado.",
        "error_code": "openrouter_error",
        "model_used": result.model_used,
        "is_fallback": result.is_fallback,
        "offline": False,
        "latency_ms": latency_ms,
    }


def _is_auth_error(message: str) -> bool:
    """Detecta erros de autentica��o/credencial do OpenRouter na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "401", "unauthorized", "authentication", "invalid api key",
        "invalid_api_key", "invalidapikey", "api key", "expired", "expirad", "insufficient",
    ]
    return any(m in lowered for m in markers)


def _is_connection_error(message: str) -> bool:
    """Detecta falhas de rede (sem internet/OpenRouter inacessível/timeouts) na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "apiconnectionerror", "connection error", "connectionerror",
        "connection reset", "reseterror", "reset", "timeout", "timed out",
        "dns", "max retries", "cannot connect", "network", "connection aborted",
        "unreachable", "ssl", "tls", "failed to resolve", "500", "502", "503", "504",
        "overloaded", "temporarily", "falha transitória",
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
        if _is_sensitive_path(child):
            continue
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
    if _is_sensitive_path(p):
        raise HTTPException(status_code=403, detail="Acesso a arquivos sensíveis bloqueado.")
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
    if _is_sensitive_path(p):
        raise HTTPException(status_code=403, detail="Acesso a arquivos sensíveis bloqueado.")
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
                candidate.relative_to(DASHBOARD_DIST.resolve())
                if full_path and candidate.is_file():
                    return FileResponse(candidate)
            except ValueError:
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