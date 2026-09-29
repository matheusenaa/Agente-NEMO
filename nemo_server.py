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
import logging
import os
import re
import secrets
import shlex
import subprocess
import sys
import threading
import time
import unicodedata
import uuid as uuid_lib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from openrouter_client import TOOL_CALL_MARKER, CompletionResult, OpenRouterClient
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

# ---------------------------------------------------------------------------
# Logs (missão §31/§32). Um logger de verdade no lugar dos `except: pass` que
# escondiam falhas de persistência. NUNCA registra senha, token ou API key:
# `_redact` garante isso mesmo se alguém passar um valor sensível por engano.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("NEMO_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
LOG = logging.getLogger("synop")

_SECRET_KEYS = ("password", "senha", "token", "api_key", "apikey", "secret", "authorization", "encrypted")


def _redact(value: Any) -> Any:
    """Remove credenciais de qualquer payload antes de logar."""
    if isinstance(value, dict):
        return {k: ("***" if any(s in str(k).lower() for s in _SECRET_KEYS) else _redact(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    text = str(value)
    if len(text) > 2000:
        return text[:2000] + "…"
    return text


def warn(context: str, exc: BaseException, **extra: Any) -> None:
    """Substitui os `except Exception: pass`: o erro SAI no log do servidor."""
    LOG.warning("%s | %s: %s | %s", context, type(exc).__name__, _redact(str(exc)),
                _redact(extra) if extra else "")


def _internal_error(context: str, exc: BaseException, status_code: int = 500) -> HTTPException:
    """Erro 500 sem vazar internals (SQL, nomes de tabela, dica do Postgres).

    `detail=str(exc)` expunha ao cliente o erro cru do Supabase, por exemplo
    `{'message': 'invalid input syntax for type uuid: "None"', 'code': '22P02',
    'hint': None, ...}`. O detalhe vai para o log do servidor; o cliente recebe
    uma mensagem genérica."""
    warn(context, exc)
    return HTTPException(
        status_code=status_code,
        detail="Não foi possível concluir a operação agora. Tente novamente.",
    )


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

# General API rate limiter (per IP)
API_RATE_LIMIT_PER_MINUTE = max(1, int(os.getenv("NEMO_API_RATE_LIMIT", "120")))
API_RATE_LIMITER = _SlidingWindowRateLimit(API_RATE_LIMIT_PER_MINUTE)

# Sync rate limiter (more permissive)
SYNC_RATE_LIMIT_PER_MINUTE = max(1, int(os.getenv("NEMO_SYNC_RATE_LIMIT", "60")))
SYNC_RATE_LIMITER = _SlidingWindowRateLimit(SYNC_RATE_LIMIT_PER_MINUTE)

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


def _safe_json(value: Any, default: str = "{}") -> str:
    """`json.dumps` que nunca explode.

    Os argumentos de uma tool call vêm do modelo e de mocks nos testes; um
    valor não serializável não pode derrubar a conversa inteira (500 no chat).
    """
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)
    except Exception:
        return default


def _needs_search(message: str, tools: List[str]) -> bool:
    """Heurística barata: a pergunta pede informação externa/recente?

    Só é a PRIMEIRA triagem. Quando ela diz "não", ainda assim o modelo pode
    pedir a ferramenta `web_search` durante a conversa (tool calling real) —
    este filtro evita só o desperdício de sempre_search em perguntas de
    conhecimento estável ("qual a capital do Brasil?").
    """
    if not (message or "").strip() or len(message.strip()) < 12:
        return False
    if "web_search" not in tools and "search" not in tools:
        return False
    msg = message.lower()
    if SEARCH_QUERY_ROOTS.search(message):
        return True
    return any(hint in msg for hint in SEARCH_HINTS)


# Ferramenta real de tool calling (§10). O modelo decide quando usá-la; o
# backend executa; o resultado volta para o modelo.
WEB_SEARCH_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Pesquise informações ATUAIS na internet (notícias, preços, resultados, "
            "datas, pessoas, eventos). Use SEMPRE que a resposta depender de algo "
            "recente ou de um fato que você não tem certeza. NÃO use para perguntas "
            "de conhecimento estável (ex.: capital de um país, fórmula, definição)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Termo de busca em português, específico e curto.",
                }
            },
            "required": ["query"],
        },
    },
}


def _search_block(sres: Dict[str, Any]) -> str:
    """Contexto de busca para o prompt, com as fontes reais.

    Quando a busca falha, o bloco DIZ que falhou — o modelo é instruído a
    informar isso ao usuário em vez de preencher a lacuna com suposição (§9).
    """
    if not sres.get("ok"):
        return (
            "AVISO — A BUSCA NA WEB FALHOU NESTA TENTATIVA.\n"
            f"Motivo informado pelo sistema: {sres.get('error') or 'mecanismo indisponível'}.\n"
            "Responda a partir do seu conhecimento, deixe isso CLARO ao usuário "
            "('não consegui confirmar na web agora') e NUNCA invente fatos, "
            "datas, números ou URLs."
        )
    results = sres.get("results", [])
    lines = [
        "INFORMAÇÕES ENCONTRADAS NA WEB AGORA (use e cite as fontes abaixo):",
        f"Mecanismo: {sres.get('provider', '')}",
    ]
    for i, r in enumerate(results[:6], 1):
        url = r.get("url") or "(fonte sem URL)"
        lines.append(
            f"\n{i}. {r.get('title') or '(sem título)'}\n"
            f"   FONTE: {url}\n"
            f"   TRECHO: {(r.get('snippet') or '')[:600]}"
        )
    lines.append(
        "\nREGRAS: separe o que vem da web do que é conhecimento seu; "
        "cite a fonte ao lado de cada informação; "
        "NÃO invente fontes, URLs ou números que não estejam acima."
    )
    return "\n".join(lines)


def _memory_block(user_id: str, agent_id: str) -> str:
    """Memória permanente do agente para este usuário (missão §24/25)."""
    try:
        mems = DATA_STORE.list_memories(user_id, agent_id) or []
    except Exception as exc:
        warn("chat: leitura de memorias", exc, user=user_id, agent=agent_id)
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
            "body": meta.get("body", ""),
            "version": meta.get("version", "1.0.0"),
            "file": path.relative_to(ROOT).as_posix(),
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


def _build_system_prompt(agent: Dict[str, Any], extra_context: str = "", can_search: bool = False) -> str:
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
    search_line = (
        "- Você PODE e DEVE usar a ferramenta `web_search` quando a resposta depender "
        "de informação atual, recente ou verificável na internet. Depois de pesquisar, "
        "cite as fontes.\n"
        "- Se a busca falhar, diga claramente ao usuário que não conseguiu consultar a web "
        "nesta tentativa. NUNCA preencha a lacuna com suposição apresentada como fato.\n"
        if can_search else
        "- Você NÃO tem acesso à internet nesta resposta. Se a pergunta exigir informação "
        "atual ou verificável, diga isso claramente ao usuário em vez de inventar.\n"
    )
    return (
        f"Você é {name} ({title}) — um agente de IA da equipe NEMO IDE.\n\n"
        f"PERSONA:\n{persona_text}{extra}\n\n"
        "DIRETRIZES:\n"
        "- Responda em português do Brasil.\n"
        "- **Responda EXATAMENTE o que foi perguntado.** Se a pergunta é factual e direta, "
        "seja direto. Se for sobre a sua área, use todo o seu conhecimento specialised. "
        "Nunca responda com uma frase genérica sobre si mesmo quando a pergunta é sobre "
        "outro assunto.\n"
        "- Seja direto e objetivo; profundidade proporcional à complexidade.\n"
        "- Nunca invente fatos, dados ou números; se não souber, diga que não sabe.\n"
        f"{search_line}"
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
    """Arquivo legado de eventos (JSON local). Só é lido para MIGRAR eventos
    antigos para o banco — a partir daí o calendário vive no DataStore."""
    return AUTH_STORE.events_file(user_id)


def _legacy_events_for(user_id: str) -> List[Dict[str, Any]]:
    return _load_events(_events_file_for(user_id))


def _migrate_legacy_events(user_id: str) -> int:
    """Importa eventos que ficaram só no JSON local para o banco de dados.

    Sem isso, quem criou eventos antes desta correção perderia o calendário ao
    trocar o backend. Roda uma vez por usuário: o arquivo é arquivado depois.
    """
    if DATA_STORE.name == "local":
        return 0
    try:
        legacy = _legacy_events_for(user_id)
    except Exception as exc:
        warn("calendario: leitura do legado", exc, user=user_id)
        return 0
    if not legacy:
        return 0
    migrated = 0
    for ev in legacy:
        try:
            if not ev.get("id"):
                ev["id"] = _gen_event_id()
            if DATA_STORE.save_event(user_id, ev):
                migrated += 1
        except Exception as exc:
            warn("calendario: migracao de evento legado", exc, user=user_id, event=ev.get("id"))
    if migrated:
        try:
            _events_file_for(user_id).replace(_events_file_for(user_id).with_suffix(".migrated.json"))
            LOG.info("calendario: %d evento(s) legado(s) migrado(s) para %s", migrated, DATA_STORE.name)
        except Exception as exc:
            warn("calendario: arquivamento do legado", exc, user=user_id)
    return migrated


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

# Security Headers Middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co https://openrouter.ai https://api.groq.com https://api.openai.com https://generativelanguage.googleapis.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # Additional security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # HSTS for production (only if HTTPS)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting por IP para endpoints gerais da API."""
    if request.url.path.startswith("/api/"):
        if request.url.path.startswith("/api/nemo/chat"):
            pass  # Chat já tem seu próprio rate limit por usuário
        elif request.url.path.startswith("/api/nemo/sync"):
            limiter = SYNC_RATE_LIMITER
            key = f"sync:{request.client.host}" if request.client else "sync:unknown"
        else:
            limiter = API_RATE_LIMITER
            key = f"api:{request.client.host}" if request.client else "api:unknown"
        
        if 'limiter' in locals() and not limiter.allow(key):
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please slow down."},
                status_code=429,
                headers={"Retry-After": "60"}
            )
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
    # `conversation_id` chega como null de clientes que ainda não têm thread
    # (o frontend envia `""`, mas APIs externas mandam null). Antes, null
    # derrubava a requisição inteira com 422 antes mesmo de gerar a resposta.
    conversation_id: Optional[str] = Field(default="", max_length=100)
    # Provedor desejado ("gemini", "groq", "openai", "openrouter"). Vazio = usa
    # a escolha da Central de IA. Antes esse campo não existia e o chat era
    # sempre OpenRouter, ignorando a configuração do usuário.
    provider: str = Field(default="", max_length=40)
    # O cliente marca aqui que esta é a PRIMEIRA mensagem de uma nova thread.
    # Sem isso, o servidor cairia no "convs[0]" e todas as conversas voltariam a
    # se misturar num histórico só.
    new_conversation: bool = False
    # "auto" (padrão) = o servidor decide se precisa buscar; "on"/"off" = força.
    web_search: str = Field(default="auto", max_length=8)



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

@app.get("/health", include_in_schema=False)
@app.get("/healthz", include_in_schema=False)
def liveness() -> Dict[str, Any]:
    """Liveness/readiness mínimo para o health check do Render.

    NÃO depende de OpenRouter, Supabase, WebSocket nem de assets: se qualquer
    serviço externo estiver fora, o processo continua saudavel e o dashboard
    ainda abre. Só falha se o próprio processo não estiver respondendo.
    """
    return {"status": "ok", "service": PROJECT_NAME, "version": VERSION, "time": datetime.now().isoformat()}


@app.get("/api/nemo/health")
def health(request: Request) -> Dict[str, Any]:
    """Health check detalhado.

    Cada sonda e isolada: uma dependencia externa quebrada (Supabase sem
    credencial, OpenRouter sem chave, pasta de squads inacessivel) NAO pode
    transformar o diagnostic em HTTP 500 — no maximo o campo vem com o erro.
    """

    def probe(fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - diagnostico nunca deve derrubar
            return f"erro: {type(exc).__name__}: {exc}"[:200]

    ai = {
        "providers_configured": probe(
            lambda: [p for p in AI_SERVICE.provider_catalog() if p["configured"]]
        ),
        "default_provider": probe(AI_SERVICE.default_provider),
        "default_model": probe(AI_SERVICE.default_provider_model),
        "web_search": probe(WEB_SEARCH_SERVICE.available_providers),
        "store_backend": probe(lambda: DATA_STORE.name),
        "encryption": probe(lambda: KEY_STORE.available),
    }
    return {
        "project": PROJECT_NAME,
        "version": VERSION,
        "time": datetime.now().isoformat(),
        "api_key_configured": probe(lambda: get_client().has_valid_key_format()),
        "models": probe(lambda: len(OPENROUTER_MODELS)),
        "agents": probe(lambda: len(_discover_agents())),
        "squads": probe(
            lambda: len(
                [d for d in SQUADS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))]
            )
            if SQUADS_DIR.is_dir()
            else 0,
        ),
        "squad_ws": False,
        "auth": True,
        "ai": ai,
        "authenticated": probe(lambda: bool(_current_user(request))),
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
    if os.environ.get("NEMO_OPEN_REGISTRATION", "1").strip() == "0":
        raise HTTPException(status_code=403, detail="Cadastro aberto desativado. Peça acesso a um administrador.")
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


class BootstrapRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""


@app.post("/api/auth/bootstrap")
def bootstrap(req: BootstrapRequest) -> Dict[str, Any]:
    """Cria o primeiro administrador (e-mail ADMIN_EMAIL) ou promove a conta existente."""
    try:
        user, created = AUTH_STORE.bootstrap_admin(req.name, req.email, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    return {"ok": True, "user": user, "created": created}


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
    admin = _require_admin(request)
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


class AdminCreateUserRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    role: str = "user"


@app.post("/api/admin/users")
def admin_create_user(req: AdminCreateUserRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
    try:
        user = AUTH_STORE.create_user(req.name, req.email, req.password, req.role)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    return {"ok": True, "user": user}


class AdminResetPasswordRequest(BaseModel):
    password: str = ""


@app.put("/api/admin/users/{user_id}/password")
def admin_reset_password(user_id: str, req: AdminResetPasswordRequest, request: Request) -> Dict[str, Any]:
    _require_admin(request)
    try:
        user = AUTH_STORE.reset_password(user_id, req.password)
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
# Calendário — eventos persistidos no DataStore (Supabase em produção)
# ---------------------------------------------------------------------------

def _gen_event_id() -> str:
    """UUID completo.

    Antes era `uuid4().hex[:9]`: o JSON local aceitava, mas a coluna
    `calendar_events.id` é do tipo `uuid` no Postgres e rejeitava com
    `22P02 invalid input syntax for type uuid`, o que fazia TODO evento
    falhar com 503.
    """
    return str(uuid4())


@app.get("/api/nemo/events")
def list_events(request: Request) -> List[Dict[str, Any]]:
    user = _require_user(request)
    _migrate_legacy_events(user["id"])
    try:
        events = DATA_STORE.list_events(user["id"]) or []
    except Exception as exc:
        warn("calendario: listagem", exc, user=user["id"], backend=DATA_STORE.name)
        events = _legacy_events_for(user["id"])
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
    if not event.get("date"):
        raise HTTPException(status_code=400, detail="Informe a data do evento.")
    _migrate_legacy_events(user["id"])
    try:
        saved = DATA_STORE.save_event(user["id"], event)
    except Exception as exc:
        warn("calendario: criacao", exc, user=user["id"], backend=DATA_STORE.name)
        raise HTTPException(status_code=503, detail="Não foi possível salvar o evento agora. Tente novamente.")
    return saved or event


@app.put("/api/nemo/events/{event_id}")
def update_event(event_id: str, req: EventRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    _migrate_legacy_events(user["id"])
    try:
        current = next((e for e in (DATA_STORE.list_events(user["id"]) or []) if e.get("id") == event_id), None)
    except Exception as exc:
        warn("calendario: leitura para atualizacao", exc, user=user["id"])
        current = next((e for e in _legacy_events_for(user["id"]) if e.get("id") == event_id), None)
    if not current:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    merged = {**current, **{k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}}
    merged["id"] = event_id
    try:
        return DATA_STORE.save_event(user["id"], _normalize_event(merged)) or merged
    except Exception as exc:
        warn("calendario: atualizacao", exc, user=user["id"])
        raise HTTPException(status_code=503, detail="Não foi possível atualizar o evento agora.")


@app.delete("/api/nemo/events/{event_id}")
def delete_event(event_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    _migrate_legacy_events(user["id"])
    try:
        ok = DATA_STORE.delete_event(user["id"], event_id)
    except Exception as exc:
        warn("calendario: exclusao", exc, user=user["id"])
        raise HTTPException(status_code=503, detail="Não foi possível excluir o evento agora.")
    if not ok:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")
    return {"ok": True, "deleted": event_id}


def _user_ai_settings(user_id: str) -> Dict[str, Any]:
    """Configuração de IA do usuário (provedor/modelo escolhidos na Central de IA).
    Nunca levanta: ausente ou quebrado é o mesmo que "não configurou"."""
    try:
        return DATA_STORE.get_ai_settings(user_id) or {}
    except Exception as exc:
        warn("ia: leitura das preferencias", exc, user=user_id)
        return {}


def _provider_is_usable(provider: str, user_id: str) -> bool:
    """Provedor só vale se tiver chave: do ambiente ou do cofre do usuário."""
    if provider not in PROVIDER_META:
        return False
    if AI_SERVICE.has_system_key(provider):
        return True
    try:
        return bool(DATA_STORE.get_api_key(user_id, provider))
    except Exception as exc:
        warn("ia: leitura do cofre de chaves", exc, user=user_id)
        return False


def _agent_override(user_id: str, agent_id: str) -> Dict[str, Any]:
    """Override de IA salvo para um agente na Central de IA (provider/modelo).

    A Central de IA grava `agent_overrides` desde o começo, mas o chat nunca
    lia esse campo: o usuário configurava "este agente usa o Groq" e o SYNOP
    ignorava a configuração."""
    if not user_id or not agent_id:
        return {}
    ov = (_user_ai_settings(user_id).get("agent_overrides") or {}).get(agent_id) or {}
    return ov if isinstance(ov, dict) else {}


def _resolve_provider(req: ChatRequest, user_id: str) -> str:
    """Provedor efetivo do chat, do mais específico ao mais geral.

    Ordem: request explícito > override do agente > default do usuário >
    `NEMO_AI_PROVIDER` do servidor > openrouter.

    Regressão estrutural: o chat usava `get_client()` (OpenRouter) direto e
    ignorava a Central de IA. Com a conta do OpenRouter sem crédito, o SYNOP
    ficava 100% offline mesmo tendo `GEMINI_API_KEY` funcionando — a escolha de
    provedor salva pelo usuário não valia nada."""
    agent_id = str(getattr(req, "agent", "") or "")
    candidates = [
        str(getattr(req, "provider", "") or ""),
        str(_agent_override(user_id, agent_id).get("provider") or ""),
        str(_user_ai_settings(user_id).get("default_provider") or ""),
        str(AI_SERVICE.default_provider() or ""),
    ]
    for raw in candidates:
        candidate = raw.strip().lower()
        if candidate and candidate in PROVIDER_META and _provider_is_usable(candidate, user_id):
            return candidate
    return "openrouter"


def _provider_model(user_id: str, provider: str, agent_model: str, agent_id: str = "") -> tuple:
    """Traduz o modelo do agente para o vocabulário do provedor escolhido.

    `deepseek/deepseek-chat` não existe no Gemini; usar o slug cru lá devolve
    404 e o usuário vê um erro de modelo em vez de resposta."""
    if provider == "openrouter":
        mi = get_model_by_id(agent_model)
        return agent_model, list(mi.fallback_slugs or []) if mi else []
    models = list(PROVIDER_META.get(provider, {}).get("models") or [])
    settings = _user_ai_settings(user_id)
    # Específico antes do genérico: request/agente, override do agente,
    # default do usuário, primeiro modelo do provedor.
    for candidate in (
        agent_model,
        str(_agent_override(user_id, agent_id).get("model") or ""),
        str(settings.get("default_model") or ""),
    ):
        if candidate and candidate in models:
            return candidate, []
    if models:
        return models[0], []
    return AI_SERVICE.default_provider_model(), []


def _generate_sync(provider: str, model: str, messages: List[Dict[str, str]],
                   temperature: float, max_tokens: int,
                   fallback_slugs: Optional[List[str]] = None) -> CompletionResult:
    """Gera a resposta pelo provedor efetivo. OpenRouter tem o caminho rico
    (tools/fallback); os demais usam o `AIProviderService`."""
    if provider == "openrouter":
        return get_client().chat_completion(
            model=model, messages=messages, temperature=temperature,
            max_tokens=max_tokens, fallback_slugs=fallback_slugs,
        )
    return AI_SERVICE.complete(
        provider, model, messages, temperature=temperature, max_tokens=max_tokens,
    )


def _resolve_agent_and_model(req: ChatRequest, user_id: str = "") -> Dict[str, Any]:
    """Resolve persona + provedor + modelo. Separate para o endpoint síncrono e o de
    streaming compartilharem exatamente a mesma decisão."""
    agent = _agent_persona(req.agent) or {
        "id": req.agent, "name": "Nemo", "title": "Assistente", "category": "assistant",
        "role": "Assistente pessoal.", "defaultModel": CATEGORY_MODEL_DEFAULT,
    }
    provider = _resolve_provider(req, user_id) if user_id else "openrouter"
    agent_model = req.model or agent.get("defaultModel") or CATEGORY_MODEL_DEFAULT
    model, fallback_slugs = _provider_model(user_id, provider, agent_model, str(req.agent or ""))
    if provider == "openrouter":
        if get_model_by_id(model) is None:
            raise HTTPException(status_code=400, detail="Modelo não configurado para o NEMO.")
    return {"agent": agent, "model": model, "provider": provider,
            "fallback_slugs": list(fallback_slugs or [])}


def _load_history(user_id: str, conversation_id: Optional[str], limit: int = 12) -> List[Dict[str, str]]:
    """Histórico da thread vindo do BANCO, não do cliente.

    Regressão grave de memória: as mensagens eram gravadas (o histórico aparecia
    na tela) mas nunca voltavam para o prompt. Bastava recarregar a página, logar
    de novo ou abrir em outro dispositivo para o agente "esquecer" tudo — a
    memória do SYNOP era só de fachada."""
    if not conversation_id:
        return []
    try:
        stored = DATA_STORE.list_messages(user_id, conversation_id) or []
    except Exception as exc:
        warn("memoria: leitura do historico", exc, user=user_id, conversation=conversation_id)
        return []
    out: List[Dict[str, str]] = []
    for m in stored[-limit:]:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content[:8000]})
    return out


def _build_messages(req: ChatRequest, system: str,
                    history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """Monta as mensagens do modelo.

    A memória vem do servidor (argumento `history`). O `req.messages` do cliente
    só entra quando o banco não tem nada — assim não duplicamos o mesmo turno
    quando o frontend também manda o histórico, e ainda respeitamos clientes
    externos que cuidam do contexto sozinhos."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    else:
        for m in req.messages[-12:]:
            if m.role in ("user", "assistant") and m.content:
                messages.append({"role": m.role, "content": m.content[:12000]})
    if req.message:
        messages.append({"role": "user", "content": req.message[:12000]})
    if len(messages) == 1:
        messages.append({"role": "user", "content": "Olá."})
    return messages


def _run_web_search(user_id: str, agent_id: str, query: str) -> Dict[str, Any]:
    """Executa a busca e registra. Nunca levanta: devolve o dicionário com
    `ok: False` para que o prompt diga ao usuário que a busca falhou."""
    try:
        res = WEB_SEARCH_SERVICE.search(user_id, query, 6)
    except WebSearchError as exc:
        LOG.info("busca indisponivel | user=%s | %s", user_id, exc.message)
        return {"ok": False, "query": query, "results": [], "error": exc.message}
    except Exception as exc:
        warn("busca: falha inesperada", exc, user=user_id, query=query[:80])
        return {"ok": False, "query": query, "results": [], "error": "Falha inesperada na busca."}
    if res.get("ok"):
        try:
            DATA_STORE.save_search(user_id, agent_id, query, res.get("provider", ""), res.get("results", []))
        except Exception as exc:
            warn("busca: persistencia", exc, user=user_id)
        _log_activity(user_id, agent_id, "web_search", "ok", res.get("provider", ""))
        LOG.info("busca ok | user=%s agent=%s provedor=%s resultados=%d",
                 user_id, agent_id, res.get("provider"), len(res.get("results") or []))
    else:
        LOG.info("busca sem resultado | user=%s provedor=%s", user_id, res.get("provider", "none"))
    return res


def _tools_for_agent(agent_id: str) -> List[Dict[str, Any]]:
    """Ferramentas expostas ao modelo — somente as permitidas ao agente."""
    allowed = AGENT_TOOLS.get(agent_id or "", [])
    if "web_search" in allowed or "search" in allowed:
        return [WEB_SEARCH_TOOL]
    return []


def _prepare_chat(req: ChatRequest, user: Dict[str, Any], resolved: Dict[str, Any],
                  on_event: Optional[Any] = None) -> Dict[str, Any]:
    """FASE 1 (comum ao chat normal e ao streaming): persona, contexto,
    eventual busca na web e montagem das mensagens.

    Separar esta fase é o que permite que o SSE execute a MESMA busca e
    depois emita os tokens — sem duplicar lógica nem divergir de comportamento.
    """
    emit = on_event or (lambda *_a, **_k: None)
    agent = resolved["agent"]
    model = resolved["model"]
    tools = _tools_for_agent(agent["id"])
    can_search = bool(tools)

    ctx_parts: List[str] = []
    mem = _memory_block(user["id"], agent["id"])
    if mem:
        ctx_parts.append(mem)
    if req.context:
        ctx_parts.append(f"CONTEXTO DO USUÁRIO:\n{req.context[:4000]}")

    used_search = False
    search_report: Dict[str, Any] = {}
    tool_message: Optional[str] = None

    # --- Etapa 1: triagem por heurística (evita custo em pergunta estável) ---
    if can_search and _needs_search(req.message, AGENT_TOOLS.get(agent["id"], [])):
        emit("status", {"stage": "searching", "message": "Consultando a web..."})
        search_report = _run_web_search(user["id"], agent["id"], req.message[:200])
        used_search = True
        ctx_parts.append(_search_block(search_report))
        _log_activity(user["id"], agent["id"], "web_search_auto",
                      "ok" if search_report.get("ok") else "unavailable", search_report.get("provider", ""))

    system = _build_system_prompt(agent, "\n\n".join(ctx_parts), can_search=can_search)
    messages = _build_messages(req, system, _load_history(user["id"], req.conversation_id))

    # Só o cliente do OpenRouter expõe tool calling e streaming. Nos demais
    # provedores a decisão de busca fica com a heurística da etapa 1 (ou com a
    # instrução no prompt) — melhor uma resposta sem tool do que responder pelo
    # provedor errado.
    provider = resolved.get("provider", "openrouter")
    c = get_client()
    if provider == "openrouter" and not c.has_valid_key_format():
        return {"__key_missing__": True, "model": model, "agent": agent, "messages": messages,
                "tools": tools, "can_search": can_search, "resolved": resolved}

    # --- Etapa 2: tool calling real (o MODELO decide pedir a ferramenta) ---
    if can_search and not used_search and provider == "openrouter":
        first = c.chat_completion_with_tools(
            model=model, messages=messages, tools=tools,
            temperature=req.temperature, max_tokens=req.max_tokens,
            fallback_slugs=resolved["fallback_slugs"],
        )
        if first.success and first.tool_calls:
            call = first.tool_calls[0]
            query = str((call.get("arguments") or {}).get("query") or req.message)[:200]
            emit("tool", {"name": "web_search", "query": query})
            emit("status", {"stage": "searching", "message": f"Pesquisando: {query}"})
            report = _run_web_search(user["id"], agent["id"], query)
            used_search = True
            search_report = report
            # O resultado volta para o MODELO como contexto, não para o usuário cru.
            block = _search_block(report)
            call_id = str(call.get("id") or "call_0")
            messages.append({"role": "assistant", "content": "", "tool_calls": [
                {"id": call_id, "type": "function",
                 "function": {"name": "web_search",
                              "arguments": _safe_json(call.get("arguments"))}}
            ]})
            messages.append({"role": "tool",
                             "tool_call_id": call_id,
                             "content": block})
            tool_message = block
            _log_activity(user["id"], agent["id"], "web_search_tool",
                          "ok" if report.get("ok") else "unavailable", report.get("provider", ""))
        elif first.success and first.content:
            # O modelo respondeu direto, sem precisar da ferramenta.
            return {
                "preanswered": first, "model": first.model_used or model, "agent": agent,
                "messages": messages, "tools": tools, "can_search": can_search,
                "used_search": False, "search_report": {},
            }

    return {
        "model": model, "agent": agent, "messages": messages, "tools": tools,
        "can_search": can_search, "used_search": used_search,
        "search_report": search_report, "tool_message": tool_message,
        "resolved": resolved,
    }


def _agentic_chat(req: ChatRequest, user: Dict[str, Any], resolved: Dict[str, Any],
                  on_event: Optional[Any] = None) -> Dict[str, Any]:
    """Fluxo completo do chat: persona → contexto → decisão de busca → modelo.

    É o mesmo caminho para `/api/nemo/chat` e `/api/nemo/chat/stream`
    (missão §6/§10):

        mensagem → agente → tools → [busca na web] → contexto → modelo → resposta
    """
    prep = _prepare_chat(req, user, resolved, on_event)
    if prep.get("__key_missing__"):
        return prep
    if prep.get("preanswered"):
        return {"result": prep["preanswered"], "model": prep["model"], "agent": prep["agent"],
                "latency_ms": round(prep["preanswered"].latency_ms, 1), "used_search": False,
                "search_report": {}}

    agent = prep["agent"]
    model = prep["model"]
    provider = resolved.get("provider", "openrouter")
    started = time.perf_counter()
    result = _generate_sync(
        provider, model, prep["messages"], req.temperature, req.max_tokens,
        fallback_slugs=resolved.get("fallback_slugs"),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "result": result, "model": model, "agent": agent, "provider": provider,
        "latency_ms": latency_ms, "used_search": prep["used_search"],
        "search_report": prep["search_report"],
    }


def _chat_failure_response(result: Any, req: ChatRequest, model: str, agent: Dict[str, Any],
                           latency_ms: float, provider: str = "openrouter") -> Dict[str, Any]:
    """Converte uma CompletionResult com erro numa resposta honesta para o usuário.

    O rótulo acompanha o provedor real: chamar Gemini e responder "chave do
    OpenRouter inválida" é errado e manda o usuário corrigir o serviço errado."""
    provider = getattr(result, "provider", None) or provider or "openrouter"
    if provider != "openrouter":
        detail = (result.error_message or "")[:300]
        return {
            "ok": False, "agent": req.agent, "error_code": "ai_error",
            "error": f"Falha ao chamar o provedor {_provider_name(provider)}.",
            "content": (
                f"⚠️ Não consegui concluir a solicitação no provedor "
                f"**{_provider_name(provider)}**.\n\n"
                "Tente outro provedor na Central de IA ou tente novamente em instantes."
            ),
            "detail": detail, "provider": provider,
            "model_used": result.model_used or model, "is_fallback": False,
            "offline": False, "latency_ms": latency_ms,
        }
    if _is_credits_error(result.error_message or ""):
        return {
            "ok": False, "agent": req.agent, "error_code": "openrouter_no_credits",
            "error": "A conta do OpenRouter está sem crédito.",
            "content": (
                "⚠️ O acesso ao OpenRouter foi recusado por falta de crédito na conta "
                "(HTTP 402 — a chave é válida, mas a conta não tem saldo).\n\n"
                "Para voltar a responder: adicione créditos em "
                "openrouter.ai/settings/credits e tente novamente. Não é preciso "
                "trocar a chave."
            ),
            "model_used": result.model_used or model, "is_fallback": False,
            "offline": True, "latency_ms": latency_ms,
        }
    if _is_auth_error(result.error_message or ""):
        return {
            "ok": False, "agent": req.agent, "error_code": "openrouter_auth",
            "error": "Credencial do OpenRouter inválida ou expirada.",
            "content": (
                "⚠️ Minha chave de acesso ao OpenRouter está inválida ou expirada (HTTP 401), "
                "então não consigo chamar modelos de IA no momento.\n\n"
                "Para voltar a responder: troque `OPENROUTER_API_KEY` no `.env` por uma chave "
                "válida e reinicie o servidor."
            ),
            "model_used": result.model_used or model, "is_fallback": False,
            "offline": True, "latency_ms": latency_ms,
        }
    if _is_connection_error(result.error_message or ""):
        return {
            "ok": False, "agent": req.agent, "error_code": "openrouter_unavailable",
            "error": "OpenRouter temporariamente inacessível.",
            "content": (
                "⚠️ Não consegui acessar o OpenRouter agora (rede indisponível ou "
                "bloqueada), então não consigo chamar modelos de IA neste momento.\n\n"
                "Verifique sua conexão e o acesso a `openrouter.ai` e reinicie o servidor."
            ),
            "model_used": result.model_used or model, "is_fallback": False,
            "offline": True, "latency_ms": latency_ms,
        }
    return {
        "ok": False, "agent": req.agent, "error_code": "openrouter_error",
        "error": "Erro ao chamar o modelo selecionado.",
        "content": "Não consegui concluir a solicitação no modelo selecionado.",
        "detail": (result.error_message or "")[:300],
        "model_used": result.model_used, "is_fallback": result.is_fallback,
        "offline": False, "latency_ms": latency_ms,
    }


def _chat_without_search(req: ChatRequest, resolved: Dict[str, Any],
                         user_id: str = "") -> Dict[str, Any]:
    """Caminho degradado: responde com o modelo, sem etapa de busca.

    Usado quando a preparação falha (rede, provedor, bug). Preferimos uma
    resposta sem cites a nenhuma resposta.
    """
    agent = resolved["agent"]
    model = resolved["model"]
    provider = resolved.get("provider", "openrouter")
    if provider == "openrouter" and not get_client().has_valid_key_format():
        return {"__key_missing__": True, "model": model, "agent": agent}
    system = _build_system_prompt(agent, req.context or "", can_search=False)
    messages = _build_messages(req, system, _load_history(user_id, req.conversation_id))
    started = time.perf_counter()
    result = _generate_sync(
        provider, model, messages, req.temperature, req.max_tokens,
        fallback_slugs=resolved.get("fallback_slugs"),
    )
    return {
        "result": result, "model": model, "agent": agent, "provider": provider,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "used_search": False, "search_report": {},
    }


@app.post("/api/nemo/chat")
def chat(req: ChatRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not AI_RATE_LIMITER.allow(user["id"]):
        return {
            "ok": True, "agent": req.agent, "offline": True, "rate_limited": True, "latency_ms": 0,
            "content": (
                f"⏳ Você atingiu o limite de **{AI_REQUEST_LIMIT_PER_MINUTE}** requisições de IA "
                "por minuto. Aguarde um instante e tente de novo.\n\n"
                "O limite é ajustável em `.env` → `NEMO_AI_RATE_LIMIT`."),
        }
    resolved = _resolve_agent_and_model(req, user["id"])
    try:
        outcome = _agentic_chat(req, user, resolved)
    except Exception as exc:
        # A busca na web é um EXTRA: se ela (ou qualquer passo de preparação)
        # explodir, ainda respondemos com o modelo em vez de devolver 500.
        warn("chat: pipeline", exc, user=user["id"], agent=req.agent)
        outcome = _chat_without_search(req, resolved, user["id"])
    if outcome.get("__key_missing__"):
        return {
            "ok": False, "agent": req.agent, "error_code": "missing_key",
            "error": "OPENROUTER_API_KEY não configurada.",
            "content": (
                "⚠️ Minha chave de acesso ao OpenRouter não está configurada. Crie um "
                "arquivo `.env` a partir de `.env.example` com sua chave do OpenRouter "
                "para eu responder de verdade."
            ),
            "model_used": outcome["model"], "is_fallback": False, "offline": True, "latency_ms": 0,
        }

    agent = outcome["agent"]
    result = outcome["result"]
    model = outcome["model"]
    latency_ms = outcome["latency_ms"]

    if not result.success:
        _log_activity(user["id"], agent["id"], "chat", "error", result.provider, result.model_used, latency_ms)
        resp = _chat_failure_response(result, req, model, agent, latency_ms,
                                   provider=outcome.get("provider", "openrouter"))
        return resp

    conversation_id = _persist_chat(
        user["id"], agent["id"], req.message, result.content, req.conversation_id,
        req.new_conversation,
    ) or ""
    _log_activity(user["id"], agent["id"], "chat", "ok", result.provider, result.model_used,
                  result.latency_ms, result.prompt_tokens, result.completion_tokens, result.total_tokens)
    return {
        "ok": True,
        "agent": req.agent,
        "content": result.content,
        "conversation_id": conversation_id,
        "model_used": result.model_used,
        "provider": result.provider,
        "is_fallback": result.is_fallback,
        "latency_ms": latency_ms,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.total_tokens,
        "finish_reason": result.finish_reason,
        "used_search": outcome["used_search"],
        "search_provider": outcome["search_report"].get("provider", ""),
        "search_results": outcome["search_report"].get("results", [])[:6] if outcome["used_search"] else [],
    }


def _provider_name(provider: str) -> str:
    return PROVIDER_META.get(provider or "", PROVIDER_META["openrouter"])["name"]



def _persist_chat(user_id: str, agent_id: str, user_message: str, reply: str,
                 conversation_id: str = "", new_conversation: bool = False) -> Optional[str]:
    """Grava a troca (pergunta + resposta) na conversa CERTA do usuário.

    Antes esta função usava sempre `convs[0]`: todo o chat do agente ia para
    uma única conversa, e o histórico virava uma mistura sem separação. Agora:
      - `conversation_id` válido → continua aquela thread;
      - `new_conversation`       → sempre cria uma thread nova;
      - sem nada                → cai na conversa mais recente (legado).
    """
    conv_id = "" if new_conversation else conversation_id
    try:
        if conv_id and not DATA_STORE.conversation_belongs_to(user_id, conv_id):
            # conversation_id de outro usuário (ou inexistente) é descartado:
            # nunca mistura contexto entre contas.
            warn("chat: conversation_id recusado", ValueError("conversa não pertence ao usuário"),
                 user=user_id, conversation_id=conv_id)
            conv_id = ""
        if not conv_id and not new_conversation:
            convs = DATA_STORE.list_conversations(user_id, agent_id) or []
            if convs:
                conv_id = convs[0]["id"]
        if not conv_id:
            conv_id = (DATA_STORE.create_conversation(user_id, agent_id, (user_message or "")[:60]) or {}).get("id", "")

        if not conv_id:
            return ""
        if user_message:
            DATA_STORE.append_message(user_id, conv_id, "user", user_message[:12000], {})
        if reply:
            DATA_STORE.append_message(user_id, conv_id, "assistant", reply[:20000], {})
        return conv_id
    except Exception as exc:
        warn("chat: persistencia falhou", exc, user=user_id, agent=agent_id, conversation_id=conv_id)
        return conv_id or ""


def _log_activity(user_id: str, agent_id: str, operation: str, status: str,
                  provider: str = "", model: str = "", latency: float = 0.0,
                  prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None:
    try:
        DATA_STORE.log_activity(user_id, agent_id, operation, status, provider, model, latency,
                                prompt_tokens, completion_tokens, total_tokens)
    except Exception as exc:
        warn("atividade: log", exc, user=user_id, operation=operation)


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
    except Exception as exc:
        warn("ia/config: leitura", exc, user=user["id"], backend=DATA_STORE.name)
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
        except Exception as exc:
            warn("ia/config: leitura de overrides", exc, user=user["id"])
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
    except Exception as exc:
        warn("ia/chaves: exclusao", exc, user=user["id"])
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
        except Exception as exc:
            warn("ia/test: leitura de chave", exc, user=user["id"])
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
            except Exception as exc:
                warn("busca: persistencia do resultado", exc, user=user["id"])
            _log_activity(user["id"], agent, "web_search", "ok", res.get("provider", ""))
        else:
            LOG.info("busca sem resultado | user=%s provider=%s", user["id"], res.get("provider", "none"))
        return res
    except WebSearchError as exc:
        LOG.info("busca indisponivel | user=%s | %s", user["id"], exc.message)
        return {"ok": False, "query": query, "results": [], "error": exc.message}


@app.get("/api/nemo/ai/memories")
def ai_memories(request: Request, agent: str = "") -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "memories": DATA_STORE.list_memories(user["id"], agent or None)}
    except Exception as exc:
        raise _internal_error("memórias: listagem", exc)


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
        raise _internal_error("atividade: listagem", exc)


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
        raise _internal_error("conversas: listagem", exc)


@app.post("/api/nemo/conversations")
def conversations_create(req: ConversationRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    conv = DATA_STORE.create_conversation(user["id"], req.agent or "nemo", req.title)
    return {"ok": True, "conversation": conv}


def _valid_conversation_id(conversation_id: str) -> bool:
    """`conversations/None/messages` não é erro do banco: é cliente mandando lixo.

    Sem esta checagem o Supabase respondia 400 (`invalid input syntax for type
    uuid`) e a rota devolvia 500 — o front exibia "tente novamente" para um
    erro que só o cliente podia corrigir."""
    try:
        return str(uuid_lib.UUID(str(conversation_id))).strip() == str(conversation_id).strip()
    except (ValueError, AttributeError, TypeError):
        return False


@app.delete("/api/nemo/conversations/{conversation_id}")
def conversations_delete(conversation_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not _valid_conversation_id(conversation_id):
        raise HTTPException(status_code=400, detail="Identificador de conversa inválido.")
    try:
        deleted = DATA_STORE.delete_conversation(user["id"], conversation_id)
    except Exception as exc:
        raise _internal_error("conversas: excluir", exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return {"ok": True, "deleted": conversation_id}


@app.get("/api/nemo/conversations/{conversation_id}/messages")
def conversations_messages(conversation_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not _valid_conversation_id(conversation_id):
        raise HTTPException(status_code=400, detail="Identificador de conversa inválido.")
    try:
        return {"ok": True, "messages": DATA_STORE.list_messages(user["id"], conversation_id)}
    except Exception as exc:
        raise _internal_error("conversas: mensagens", exc)


@app.get("/api/nemo/profile")
def profile_get(request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    profile = DATA_STORE.get_profile(user["id"]) or {}
    base = {"id": user["id"], "email": user.get("email", ""), "name": user.get("name", "")}
    base.update({k: v for k, v in profile.items() if k in ("name", "email", "language", "avatar", "default_agent", "preferences")})
    return {"ok": True, "profile": base}


# ---------------------------------------------------------------------------
# Streaming SSE do chat — missão §6/§12
# A tela não pode ficar 8-20s congelada esperando a resposta inteira.
# ---------------------------------------------------------------------------

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # O nginx/X-Accel-Buffering desliga o buffer, senão o SSE chega de uma vez
    # e o efeito do streaming se perde em produção.
    "X-Accel-Buffering": "no",
}


def _sse(event: str, data: Any) -> str:
    """Serializa um evento SSE. `data` é sempre JSON (evita quebra de linha)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/nemo/chat/stream")
def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    user = _require_user(request)

    if not AI_RATE_LIMITER.allow(user["id"]):
        def limited() -> Any:
            yield _sse("error", {
                "ok": False, "rate_limited": True, "agent": req.agent,
                "error_code": "rate_limited",
                "content": (
                    f"⏳ Você atingiu o limite de **{AI_REQUEST_LIMIT_PER_MINUTE}** requisições "
                    "de IA por minuto. Aguarde um instante e tente de novo."),
            })
            yield _sse("done", {"ok": False})
        return StreamingResponse(limited(), media_type="text/event-stream", headers=SSE_HEADERS)

    try:
        resolved = _resolve_agent_and_model(req, user["id"])
    except HTTPException as exc:
        # `except ... as exc` remove a variável ao sair do bloco, e o gerador
        # SSE só roda depois — capturamos o texto aqui.
        detail = exc.detail
        def rejected() -> Any:
            yield _sse("error", {"ok": False, "agent": req.agent, "content": detail})
            yield _sse("done", {"ok": False})
        return StreamingResponse(rejected(), media_type="text/event-stream", headers=SSE_HEADERS)

    def generate() -> Any:
        started = time.perf_counter()
        used_slug = resolved["model"]
        queue: List[Dict[str, Any]] = []
        send: Any = queue.append

        def on_event(kind: str, payload: Dict[str, Any]) -> None:
            send({"type": kind, "data": payload})

        # 1) Fase de preparação (mesma do chat normal): persona, memória, busca.
        yield _sse("start", {"agent": req.agent, "model": resolved["model"]})
        try:
            prep = _prepare_chat(req, user, resolved, on_event)
        except Exception as exc:
            warn("chat/stream: preparacao", exc, user=user["id"])
            yield _sse("error", {"ok": False, "content": "Falha interna ao preparar a resposta."})
            yield _sse("done", {"ok": False})
            return

        # Esvazia o que a preparação acumulou (status/tool).
        while queue:
            item = queue.pop(0)
            yield _sse(item["type"], item["data"])

        if prep.get("__key_missing__"):
            yield _sse("error", {
                "ok": False, "agent": req.agent, "error_code": "missing_key",
                "content": (
                    "⚠️ Minha chave de acesso ao OpenRouter não está configurada. "
                    "Copie `.env.example` para `.env` com sua chave do OpenRouter para "
                    "eu responder de verdade."),
            })
            yield _sse("done", {"ok": False})
            return

        if prep.get("preanswered"):
            # O modelo já respondeu direto na rodada de tools: só repassa.
            used_slug = prep["preanswered"].model_used or used_slug
            answer = [prep["preanswered"].content or ""]
            yield _sse("delta", {"text": answer[0]})
        elif resolved.get("provider", "openrouter") != "openrouter":
            # Só o cliente do OpenRouter sabe fazer streaming token a token.
            # Em vez de fingir que streamed, avisamos e deixamos o frontend
            # cair no chat síncrono (que respeita o provedor escolhido).
            provider = resolved["provider"]
            yield _sse("error", {
                "ok": False, "agent": req.agent,
                "error_code": "stream_unsupported_provider",
                "content": (
                    f"O provedor **{provider}** não transmite resposta palavra a palavra. "
                    "Respondendo de uma vez."
                ),
                "fallback_to_sync": True,
                "provider": provider,
            })
            started = time.perf_counter()
            result = _generate_sync(
                provider, prep["model"], prep["messages"], req.temperature, req.max_tokens,
                fallback_slugs=resolved.get("fallback_slugs"),
            )
            if not result.success:
                yield _sse("error", _chat_failure_response(
                    result, req, prep["model"], prep["agent"],
                    round((time.perf_counter() - started) * 1000, 1), provider=provider,
                ))
                yield _sse("done", {"ok": False})
                return
            answer = [result.content or ""]
            yield _sse("delta", {"text": answer[0]})
        else:
            # 2) Gera token a token.
            model = prep["model"]
            c = get_client()
            slugs = [model] + [s for s in resolved["fallback_slugs"] if s and s != model]
            answer: List[str] = []
            last_error = ""
            errors_seen: List[str] = []
            for idx, slug in enumerate(slugs):
                used_slug = slug
                answer = []

                try:
                    for piece in c.stream_chat(
                        model=slug, messages=prep["messages"],
                        temperature=req.temperature, max_tokens=req.max_tokens,
                    ):
                        if piece.startswith(TOOL_CALL_MARKER):
                            # Ferramenta só é resolvida na fase de preparação;
                            # se aparecer aqui é ruído do modelo — ignora.
                            continue
                        answer.append(piece)
                        yield _sse("delta", {"text": piece})
                    break
                except Exception as exc:
                    last_error = str(exc)
                    errors_seen.append(last_error)
                    if idx < len(slugs) - 1:
                        nxt = slugs[idx + 1]
                        LOG.info("stream: %s falhou (%s), tentando %s", slug, last_error[:80], nxt)
                        # O parcial JÁ FOI emitido ao cliente (deltas são
                        # enviados assim que chegam). Mandamos o evento `reset`
                        # para ele descartar o que recebeu e mostrar o fallback.
                        # Apagar caracteres com retrocesso não é confiável.
                        yield _sse("reset", {"reason": "fallback", "model": nxt})
                        continue
                    break
            # A ÚLTIMA mensagem não é necessariamente a causa raiz: se o
            # primário cair por falta de crédito (402) e o fallback responder
            # 400 "not a valid model ID", a causa real se perde e o usuário
            # recebe um erro que não ajuda. Preferimos a primeira falha de
            # conta/credenção; o erro específico do modelo serve de detalhe.
            root_error = last_error
            for candidate in errors_seen:
                if _is_credits_error(candidate) or _is_auth_error(candidate):
                    root_error = candidate
                    break
            if not answer:
                yield _sse("error", _chat_failure_response(
                    CompletionResult(success=False, content="", model_used=used_slug,
                                    original_model=model, is_fallback=used_slug != model,
                                    latency_ms=0.0, error_message=root_error),
                    req, used_slug, prep["agent"],
                    round((time.perf_counter() - started) * 1000, 1),
                    provider=resolved.get("provider", "openrouter"),
                ))
                yield _sse("done", {"ok": False})
                return
        # 3) Persistência: só depois de gerar tudo, para não gravar parcial.
        content = "".join(answer)
        conversation_id = _persist_chat(
            user["id"], prep["agent"]["id"], req.message, content, req.conversation_id,
            req.new_conversation,
        ) or ""
        _log_activity(user["id"], prep["agent"]["id"], "chat_stream", "ok",
                      "openrouter", used_slug, round((time.perf_counter() - started) * 1000, 1))
        yield _sse("sources", {
            "provider": prep.get("search_report", {}).get("provider", ""),
            "results": prep.get("search_report", {}).get("results", [])[:6] if prep.get("used_search") else [],
        })
        yield _sse("done", {
            "ok": True, "agent": req.agent, "conversation_id": conversation_id,
            "model_used": used_slug, "used_search": prep.get("used_search", False),
        })

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


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
# A UI envia em português; o banco guarda os mesmos rótulos. Antes a validação
# aceitava só 4 de 6 valores e REBAIXAVA silenciosamente qualquer outro
# (ex.: "alta" virava "normal" sem aviso nenhum).
VALID_TASK_PRIORITY = ("urgente", "importante", "normal", "baixa")


@app.get("/api/nemo/tasks")
def tasks_list(request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    try:
        return {"ok": True, "tasks": DATA_STORE.list_tasks(user["id"])}
    except Exception as exc:
        raise _internal_error("tarefas: listagem", exc)


@app.post("/api/nemo/tasks")
def tasks_save(req: TaskRequest, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    if not (req.title or "").strip():
        raise HTTPException(status_code=400, detail="Informe o título da tarefa.")
    if req.priority not in VALID_TASK_PRIORITY:
        # Agora o cliente recebe o motivo em vez de ver a tarefa mudar sozinha.
        raise HTTPException(
            status_code=400,
            detail=f"Prioridade inválida '{req.priority}'. Use: {', '.join(VALID_TASK_PRIORITY)}.",
        )
    if req.status not in VALID_TASK_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido '{req.status}'. Use: {', '.join(VALID_TASK_STATUS)}.",
        )
    task = {
        "id": req.id or _gen_event_id(),
        "title": (req.title or "").strip() or "Tarefa sem título",
        "priority": req.priority,
        "agent_id": req.agentId or "nemo",
        "status": req.status,
        "created_at": _now_ms(),
        "due_date": req.dueDate,
        "done_at": _now_ms() if req.status == "done" else None,
    }
    try:
        DATA_STORE.save_task(user["id"], task)
    except Exception as exc:
        warn("tarefas: criacao", exc, user=user["id"], backend=DATA_STORE.name)
        raise HTTPException(status_code=503, detail="Não foi possível salvar a tarefa agora.")
    return {"ok": True, "task": task}


@app.delete("/api/nemo/tasks/{task_id}")
def tasks_delete(task_id: str, request: Request) -> Dict[str, Any]:
    user = _require_user(request)
    ok = DATA_STORE.delete_task(user["id"], task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"ok": True, "deleted": task_id}


# ---------------------------------------------------------------------------
# Sincronização Offline-First — missão §11-15
# ---------------------------------------------------------------------------


class SyncOperation(BaseModel):
    operation: Literal["create", "update", "delete"]
    store: Literal[
        "conversations", "messages", "memories", "tasks", "events",
        "ai_keys", "ai_settings", "profile", "activity_logs", "web_searches"
    ]
    data: Dict[str, Any]
    client_id: str
    timestamp: int


class SyncPushRequest(BaseModel):
    operations: List[SyncOperation]
    last_sync: Optional[int] = None


class SyncPullRequest(BaseModel):
    since: Optional[int] = None
    stores: Optional[List[str]] = None


class ConflictResolutionRequest(BaseModel):
    conflicts: List[Dict[str, Any]]


@app.post("/api/nemo/sync/push")
def sync_push(req: SyncPushRequest, request: Request) -> Dict[str, Any]:
    """Recebe operações locais do cliente e aplica no servidor.
    Retorna operações aplicadas com sucesso e conflitos detectados."""
    user = _require_user(request)
    user_id = user["id"]

    results: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    server_version = int(time.time() * 1000)

    for op in req.operations:
        try:
            result = _apply_sync_operation(user_id, op)
            if result.get("conflict"):
                conflicts.append({
                    "client_id": op.client_id,
                    "store": op.store,
                    "server_data": result.get("server_data"),
                    "local_data": op.data,
                })
                results.append({"client_id": op.client_id, "status": "conflict", "conflict": True})
            else:
                results.append({"client_id": op.client_id, "status": "ok", "server_id": result.get("server_id")})
        except Exception as exc:
            results.append({"client_id": op.client_id, "status": "error", "error": str(exc)})

    return {
        "ok": True,
        "results": results,
        "conflicts": conflicts,
        "server_version": server_version,
    }


@app.get("/api/nemo/sync/pull")
def sync_pull(
    request: Request,
    since: Optional[int] = Query(None, description="Timestamp da última sincronização"),
    stores: Optional[str] = Query(None, description="Lojas separadas por vírgula"),
) -> Dict[str, Any]:
    """Retorna mudanças no servidor desde `since`."""
    user = _require_user(request)
    user_id = user["id"]

    store_list = [s.strip() for s in (stores or "").split(",") if s.strip()] or [
        "conversations", "messages", "memories", "tasks", "events",
        "ai_keys", "ai_settings", "profile", "activity_logs", "web_searches"
    ]

    changes: Dict[str, List[Dict[str, Any]]] = {}
    server_version = int(time.time() * 1000)

    for store in store_list:
        try:
            items = _get_store_changes_since(user_id, store, since or 0)
            if items:
                changes[store] = items
        except Exception:
            changes[store] = []

    return {
        "ok": True,
        "changes": changes,
        "server_version": server_version,
    }


@app.post("/api/nemo/sync/conflicts")
def sync_resolve_conflicts(req: ConflictResolutionRequest, request: Request) -> Dict[str, Any]:
    """Resolve conflitos enviados pelo cliente (local-wins, remote-wins, merge)."""
    user = _require_user(request)
    user_id = user["id"]

    results: List[Dict[str, Any]] = []

    for conflict in req.conflicts:
        try:
            client_id = conflict.get("client_id")
            store = conflict.get("store")
            resolution = conflict.get("resolution", "local-wins")
            resolved_data = conflict.get("resolved_data")

            if resolution == "local-wins":
                _apply_local_wins(user_id, store, resolved_data)
            elif resolution == "remote-wins":
                pass
            elif resolution == "merge" and resolved_data:
                _apply_merge(user_id, store, resolved_data)

            results.append({"client_id": client_id, "status": "resolved"})
        except Exception as exc:
            results.append({"client_id": conflict.get("client_id"), "status": "error", "error": str(exc)})

    return {"ok": True, "results": results}


def _apply_sync_operation(user_id: str, op: SyncOperation) -> Dict[str, Any]:
    """Aplica uma operação de sync. Retorna {'conflict': True, 'server_data': ...} se houver conflito."""
    store = op.store
    data = op.data
    operation = op.operation

    if store == "conversations":
        if operation == "create":
            conv = DATA_STORE.create_conversation(user_id, data.get("agent_id", "nemo"), data.get("title", "Nova conversa"))
            return {"server_id": conv.get("id")}
        elif operation == "update":
            DATA_STORE.update_conversation(user_id, data["id"], data)
            return {"server_id": data["id"]}
        elif operation == "delete":
            DATA_STORE.delete_conversation(user_id, data["id"])
            return {"server_id": data["id"]}

    elif store == "messages":
        if operation == "create":
            # Nunca aceita conversation_id de outro usuário: a posse é
            # verificada ANTES de gravar (anti-IDOR / anti-contexto cruzado).
            conv_id = data.get("conversation_id", "")
            if conv_id and not DATA_STORE.conversation_belongs_to(user_id, conv_id):
                raise ValueError("conversação não pertence a este usuário")
            DATA_STORE.append_message(user_id, conv_id, data.get("role", "user"),
                                      data.get("content", ""), data.get("meta"))
            return {"server_id": "created"}
        elif operation == "delete":
            pass

    elif store == "memories":
        if operation == "create":
            mem = DATA_STORE.save_memory(user_id, data.get("agent_id", "nemo"), data["content"], data.get("kind", "obs"))
            return {"server_id": mem.get("id")}
        elif operation == "update":
            pass
        elif operation == "delete":
            DATA_STORE.delete_memory(user_id, data["id"])
            return {"server_id": data["id"]}

    elif store == "tasks":
        if operation in ("create", "update"):
            DATA_STORE.save_task(user_id, data)
            return {"server_id": data.get("id")}
        elif operation == "delete":
            DATA_STORE.delete_task(user_id, data["id"])
            return {"server_id": data["id"]}

    elif store == "events":
        if operation in ("create", "update"):
            if not data.get("id"):
                data["id"] = _gen_event_id()
            saved = DATA_STORE.save_event(user_id, data)
            return {"server_id": (saved or {}).get("id", data.get("id"))}
        elif operation == "delete":
            DATA_STORE.delete_event(user_id, data["id"])
            return {"server_id": data["id"]}

    elif store == "profile":
        DATA_STORE.save_profile(user_id, data)
        return {"server_id": "profile"}

    elif store == "ai_settings":
        DATA_STORE.save_ai_settings(user_id, data)
        return {"server_id": "ai_settings"}

    elif store == "ai_keys":
        if operation in ("create", "update"):
            DATA_STORE.save_api_key(user_id, data["provider"], data["encrypted_key"], data["masked"], data.get("model", ""), data.get("verified", False))
            return {"server_id": data["provider"]}
        elif operation == "delete":
            DATA_STORE.delete_api_key(user_id, data["provider"])
            return {"server_id": data["provider"]}

    return {"server_id": "unknown"}


def _get_store_changes_since(user_id: str, store: str, since: int) -> List[Dict[str, Any]]:
    """Retorna itens modificados desde `since` (ms epoch)."""
    items: List[Dict[str, Any]] = []

    try:
        if store == "conversations":
            items = DATA_STORE.list_conversations(user_id)
        elif store == "memories":
            items = DATA_STORE.list_memories(user_id)
        elif store == "tasks":
            items = DATA_STORE.list_tasks(user_id)
        elif store == "events":
            items = DATA_STORE.list_events(user_id)
        elif store == "ai_keys":
            items = DATA_STORE.list_api_keys(user_id)
        elif store == "profile":
            items = [DATA_STORE.get_profile(user_id)]
        elif store == "ai_settings":
            items = [DATA_STORE.get_ai_settings(user_id)]
    except Exception as exc:
        warn(f"sync/pull: leitura de {store}", exc, user=user_id)
        return []

    filtered = []
    for item in items:
        updated = item.get("updated_at") or item.get("created_at") or item.get("updatedAt") or 0
        if isinstance(updated, str):
            try:
                updated = int(datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp() * 1000)
            except Exception:
                updated = 0
        if updated > since:
            filtered.append(item)

    return filtered


def _apply_local_wins(user_id: str, store: str, data: Dict[str, Any]) -> None:
    """Força dados locais no servidor."""
    if store == "conversations":
        DATA_STORE.update_conversation(user_id, data["id"], data)
    elif store == "memories":
        pass
    elif store == "tasks":
        DATA_STORE.save_task(user_id, data)
    elif store == "events":
        DATA_STORE.save_event(user_id, data)
    elif store == "profile":
        DATA_STORE.save_profile(user_id, data)
    elif store == "ai_settings":
        DATA_STORE.save_ai_settings(user_id, data)


def _apply_merge(user_id: str, store: str, data: Dict[str, Any]) -> None:
    """Merge simples: sobrescreve campos não-nulos do local no servidor."""
    if store == "conversations":
        existing = None
        for c in DATA_STORE.list_conversations(user_id):
            if c.get("id") == data.get("id"):
                existing = c
                break
        if existing:
            merged = {**existing, **{k: v for k, v in data.items() if v is not None}}
            DATA_STORE.update_conversation(user_id, data["id"], merged)
    elif store == "tasks":
        DATA_STORE.save_task(user_id, data)
    elif store == "events":
        DATA_STORE.save_event(user_id, data)
    elif store == "profile":
        DATA_STORE.save_profile(user_id, data)


def _is_credits_error(message: str) -> bool:
    """Detecta falta de cr��dito/cota na conta do OpenRouter (HTTP 402).

    Precisa vir ANTES de `_is_auth_error`: a mensagem do OpenRouter para 402
    diz "Insufficient credits", que casaria com o marcador "insufficient" e
    faria o servidor culpar uma chave v��lida."""
    lowered = (message or "").lower()
    markers = [
        "insufficient credits", "insufficient credit", "insufficient funds",
        "insufficient quota", "payment required", "402",
        "add credits", "buy credits", "credits exceeded", "no credits",
        "cr��dito insuficiente", "credito insuficiente", "sem cr��dito", "sem credito",
        "saldo insuficiente",
    ]
    return any(m in lowered for m in markers)


def _is_auth_error(message: str) -> bool:
    """Detecta erros de autentica??o/credencial do OpenRouter na mensagem de erro."""
    lowered = (message or "").lower()
    markers = [
        "401", "unauthorized", "authentication", "invalid api key",
        "invalid_api_key", "invalidapikey", "api key", "expired", "expirad",
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