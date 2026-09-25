"""
NEMO — Camada de dados (missão §3-4, §5-6).

Abstração `DataStore` que esconde a origem da persistência:
    - SupabaseStore   → PostgreSQL + RLS via cliente Supabase (service role no backend).
    - LocalStore      → JSON em _data/users/<user_id>/ (fallback self-contained atual).

TODO por usuário:
    conversations, messages, memories, ai_keys (criptografadas), ai_settings,
    tasks, activity_logs, web_searches.

Segurança: mesmo com Supabase, o BACKEND filtra tudo por user_id em TODA
consulta (o frontend não é confiável — missão §44) e as tabelas têm RLS no
banco (missão §6). API Keys são encriptadas em repouso ANTES de entrarem na
camada de dados (ver ai_keys.py), nunca em texto puro.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from ai_keys import KeyStore, mask_key

load_dotenv()

try:
    from supabase import create_client  # type: ignore
    SUPABASE_PKG = True
except ImportError:  # pragma: no cover
    SUPABASE_PKG = False


def _now_ms() -> int:
    return int(time.time() * 1000)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class DataStore:
    name = "base"
    enabled = False

    # ---- conversas ----
    def list_conversations(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]: ...
    def create_conversation(self, user_id: str, agent_id: str, title: str) -> Dict[str, Any]: ...
    def append_message(self, user_id: str, conversation_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> None: ...
    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]: ...

    # ---- memórias dos agentes ----
    def list_memories(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]: ...
    def save_memory(self, user_id: str, agent_id: str, content: str, kind: str = "obs") -> Dict[str, Any]: ...
    def delete_memory(self, user_id: str, memory_id: str) -> bool: ...

    # ---- chaves de IA (já encriptadas) ----
    def save_api_key(self, user_id: str, provider: str, encrypted: str, masked: str, model: str = "", verified: bool = False) -> None: ...
    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]: ...
    def get_api_key(self, user_id: str, provider: str) -> Optional[str]: ...
    def delete_api_key(self, user_id: str, provider: str) -> bool: ...

    # ---- preferências de IA ----
    def get_ai_settings(self, user_id: str) -> Dict[str, Any]: ...
    def save_ai_settings(self, user_id: str, data: Dict[str, Any]) -> None: ...

    # ---- tarefas (persistência leve) ----
    def list_tasks(self, user_id: str) -> List[Dict[str, Any]]: ...
    def save_task(self, user_id: str, task: Dict[str, Any]) -> None: ...
    def delete_task(self, user_id: str, task_id: str) -> bool: ...

    # ---- atividade / logs (sem secrets) ----
    def log_activity(self, user_id: str, agent_id: str, operation: str, status: str,
                     provider: str = "", model: str = "", latency_ms: float = 0.0,
                     prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None: ...
    def list_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]: ...

    # ---- busca web persistida ----
    def save_search(self, user_id: str, agent_id: str, query: str, provider: str, results: List[Dict[str, Any]]) -> None: ...


# ---------------------------------------------------------------------------
# Fallback local (JSON em _data/users/<id>/)
# ---------------------------------------------------------------------------


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if data is not None else default
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


class LocalStore(DataStore):
    """Persistência self-contained em JSON, uma pasta privada por usuário."""

    name = "local"

    def __init__(self, root: Path, secret: bytes):
        self.root = root
        self.data_dir = root / "_data" / "users"
        self.enabled = True
        self.keystore = KeyStore(secret)

    def _dir(self, user_id: str) -> Path:
        d = self.data_dir / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _f(self, user_id: str, name: str) -> Path:
        return self._dir(user_id) / name

    # ---- conversas ----
    def list_conversations(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        if agent_id:
            convs = [c for c in convs if c.get("agent_id") == agent_id]
        convs.sort(key=lambda c: c.get("updated_at", 0), reverse=True)
        return [{k: v for k, v in c.items() if k != "messages"} | {"message_count": len(c.get("messages", []))} for c in convs]

    def create_conversation(self, user_id: str, agent_id: str, title: str) -> Dict[str, Any]:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        conv = {
            "id": "c_" + hex(int(time.time() * 1000))[2:] + hex(len(convs))[2:],
            "agent_id": agent_id,
            "title": title or "Nova conversa",
            "created_at": _now_ms(),
            "updated_at": _now_ms(),
            "messages": [],
        }
        convs.insert(0, conv)
        _write_json(self._f(user_id, "conversations.json"), convs)
        return {k: v for k, v in conv.items() if k != "messages"}

    def _find_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        for c in _read_json(self._f(user_id, "conversations.json"), []):
            if c.get("id") == conversation_id:
                return c
        return None

    def append_message(self, user_id: str, conversation_id: str, role: str, content: str,
                       meta: Optional[Dict[str, Any]] = None) -> None:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        for c in convs:
            if c.get("id") == conversation_id:
                c.setdefault("messages", []).append({
                    "role": role, "content": content, "meta": meta or {},
                    "created_at": _now_ms(),
                })
                c["updated_at"] = _now_ms()
                break
        _write_json(self._f(user_id, "conversations.json"), convs)

    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        conv = self._find_conversation(user_id, conversation_id)
        return (conv or {}).get("messages", [])

    # ---- memórias ----
    def list_memories(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        mems = _read_json(self._f(user_id, "memories.json"), [])
        if agent_id:
            mems = [m for m in mems if m.get("agent_id") == agent_id]
        mems.sort(key=lambda m: m.get("created_at", 0), reverse=True)
        return mems

    def save_memory(self, user_id: str, agent_id: str, content: str, kind: str = "obs") -> Dict[str, Any]:
        mems = _read_json(self._f(user_id, "memories.json"), [])
        mem = {
            "id": "m_" + hex(int(time.time() * 1000))[2:],
            "user_id": user_id,
            "agent_id": agent_id,
            "content": content,
            "kind": kind,
            "created_at": _now_ms(),
        }
        mems.insert(0, mem)
        mems = mems[:500]
        _write_json(self._f(user_id, "memories.json"), mems)
        return mem

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        mems = _read_json(self._f(user_id, "memories.json"), [])
        remaining = [m for m in mems if m.get("id") != memory_id]
        if len(remaining) == len(mems):
            return False
        _write_json(self._f(user_id, "memories.json"), remaining)
        return True

    # ---- chaves ----
    def save_api_key(self, user_id: str, provider: str, encrypted: str, masked: str,
                     model: str = "", verified: bool = False) -> None:
        keys = _read_json(self._f(user_id, "ai_keys.json"), {})
        keys[provider] = {
            "encrypted": encrypted, "masked": masked, "model": model,
            "verified": verified, "updated_at": _now_iso(),
        }
        _write_json(self._f(user_id, "ai_keys.json"), keys)

    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        keys = _read_json(self._f(user_id, "ai_keys.json"), {})
        return [{"provider": p, "masked": v.get("masked", ""), "model": v.get("model", ""),
                 "verified": v.get("verified", False), "updated_at": v.get("updated_at", "")}
                for p, v in sorted(keys.items())]

    def get_api_key(self, user_id: str, provider: str) -> Optional[str]:
        keys = _read_json(self._f(user_id, "ai_keys.json"), {})
        entry = keys.get(provider)
        enc = (entry or {}).get("encrypted")
        if not enc:
            return None
        try:
            return self.keystore.decrypt(enc)
        except Exception:
            return None

    def delete_api_key(self, user_id: str, provider: str) -> bool:
        keys = _read_json(self._f(user_id, "ai_keys.json"), {})
        if provider not in keys:
            return False
        keys.pop(provider, None)
        _write_json(self._f(user_id, "ai_keys.json"), keys)
        return True

    # ---- preferências de IA ----
    def get_ai_settings(self, user_id: str) -> Dict[str, Any]:
        return _read_json(self._f(user_id, "ai_settings.json"), {})

    def save_ai_settings(self, user_id: str, data: Dict[str, Any]) -> None:
        cur = self.get_ai_settings(user_id)
        cur.update({k: v for k, v in data.items() if v is not None})
        cur["updated_at"] = _now_iso()
        _write_json(self._f(user_id, "ai_settings.json"), cur)

    # ---- tarefas ----
    def list_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        tasks = _read_json(self._f(user_id, "tasks.json"), [])
        tasks.sort(key=lambda t: t.get("created_at", 0), reverse=True)
        return tasks

    def save_task(self, user_id: str, task: Dict[str, Any]) -> None:
        tasks = _read_json(self._f(user_id, "tasks.json"), [])
        tasks = [t for t in tasks if t.get("id") != task.get("id")]
        tasks.insert(0, task)
        _write_json(self._f(user_id, "tasks.json"), tasks[:500])

    def delete_task(self, user_id: str, task_id: str) -> bool:
        tasks = _read_json(self._f(user_id, "tasks.json"), [])
        remaining = [t for t in tasks if t.get("id") != task_id]
        if len(remaining) == len(tasks):
            return False
        _write_json(self._f(user_id, "tasks.json"), remaining)
        return True

    # ---- atividade ----
    def log_activity(self, user_id: str, agent_id: str, operation: str, status: str,
                     provider: str = "", model: str = "", latency_ms: float = 0.0,
                     prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None:
        acts = _read_json(self._f(user_id, "activity.json"), [])
        acts.insert(0, {
            "agent_id": agent_id, "operation": operation, "status": status,
            "provider": provider, "model": model, "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "created_at": _now_iso(),
        })
        _write_json(self._f(user_id, "activity.json"), acts[:500])

    def list_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return _read_json(self._f(user_id, "activity.json"), [])[:limit]

    # ---- search ----
    def save_search(self, user_id: str, agent_id: str, query: str, provider: str,
                    results: List[Dict[str, Any]]) -> None:
        searches = _read_json(self._f(user_id, "searches.json"), [])
        searches.insert(0, {
            "agent_id": agent_id, "query": query, "provider": provider,
            "results": results[:20], "created_at": _now_iso(),
        })
        _write_json(self._f(user_id, "searches.json"), searches[:300])


# ---------------------------------------------------------------------------
# Supabase (PostgreSQL + RLS). Serviço habilitado apenas com URL + chaves.
# ---------------------------------------------------------------------------


class SupabaseStore(DataStore):
    """Backend via Supabase. O backend usa service role e filtra por user_id
    em todas as consultas; as tabelas ainda têm RLS exigindo auth.uid()=user_id."""

    name = "supabase"

    def __init__(self, url: str, service_key: str, secret: bytes):
        self.enabled = False
        if not SUPABASE_PKG:
            return
        if not (url and service_key):
            return
        try:
            self.client = create_client(url.strip(), service_key.strip())
            self.enabled = True
        except Exception:
            self.enabled = False
            return
        self.keystore = KeyStore(secret)

    def _t(self, table: str):
        return self.client.table(table)

    # ---- conversas ----
    def list_conversations(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self._t("conversations").select("*, messages(count)").eq("user_id", user_id)
        if agent_id:
            q = q.eq("agent_id", agent_id)
        data = q.order("updated_at", desc=True).execute().data
        return [self._strip_ids(d) for d in data]

    @staticmethod
    def _strip_ids(row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row)
        if "messages" in out:
            msgs = out.pop("messages") or []
            count = 0
            if isinstance(msgs, list) and msgs:
                count = (msgs[0] or {}).get("count", 0)
            elif isinstance(msgs, dict):
                count = msgs.get("count", 0)
            out["message_count"] = count
        return out

    @staticmethod
    def _iso(ms_value: Any) -> Any:
        """Converte ms (epoch) do frontend/local em ISO para coluna timestamptz."""
        if isinstance(ms_value, (int, float)) and ms_value and ms_value > 10 ** 12:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(ms_value / 1000, tz=timezone.utc).isoformat()
        return ms_value

    @staticmethod
    def _ms(value: Any) -> Any:
        """Converte timestamptz do Supabase de volta em ms (epoch), padrão local."""
        if isinstance(value, str):
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except Exception:
                return value
        if isinstance(value, (int, float)):
            return int(value * 1000 if abs(value) < 10 ** 12 else value)
        return value

    def create_conversation(self, user_id: str, agent_id: str, title: str) -> Dict[str, Any]:
        data = {
            "user_id": user_id, "agent_id": agent_id,
            "title": title or "Nova conversa",
            "created_at": _now_iso(), "updated_at": _now_iso(),
        }
        row = self._t("conversations").insert(data).execute().data
        return self._strip_ids(row[0]) if row else {"id": None, **data}

    def append_message(self, user_id: str, conversation_id: str, role: str, content: str,
                       meta: Optional[Dict[str, Any]] = None) -> None:
        self._t("messages").insert({
            "conversation_id": conversation_id, "user_id": user_id,
            "role": role, "content": content, "meta": meta or {},
            "created_at": _now_iso(),
        }).execute()
        self._t("conversations").update({"updated_at": _now_iso()}).eq("id", conversation_id).execute()

    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        return self._t("messages").select("*").eq("conversation_id", conversation_id).eq("user_id", user_id)\
            .order("created_at").execute().data

    # ---- memórias ----
    def list_memories(self, user_id: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self._t("agent_memories").select("*").eq("user_id", user_id)
        if agent_id:
            q = q.eq("agent_id", agent_id)
        return q.order("created_at", desc=True).execute().data

    def save_memory(self, user_id: str, agent_id: str, content: str, kind: str = "obs") -> Dict[str, Any]:
        row = self._t("agent_memories").insert({
            "user_id": user_id, "agent_id": agent_id, "content": content,
            "kind": kind, "created_at": _now_iso(),
        }).execute().data
        return row[0] if row else {"agent_id": agent_id, "content": content}

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        data = self._t("agent_memories").delete().eq("id", memory_id).eq("user_id", user_id).execute().data
        return bool(data)

    # ---- chaves ----
    def save_api_key(self, user_id: str, provider: str, encrypted: str, masked: str,
                     model: str = "", verified: bool = False) -> None:
        self._t("user_ai_keys").upsert({
            "user_id": user_id, "provider": provider, "encrypted_key": encrypted,
            "masked": masked, "model": model, "verified": verified, "updated_at": _now_iso(),
        }, on_conflict="user_id,provider").execute()

    def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        data = self._t("user_ai_keys").select("provider,masked,model,verified,updated_at")\
            .eq("user_id", user_id).execute().data
        return list(data)

    def get_api_key(self, user_id: str, provider: str) -> Optional[str]:
        data = self._t("user_ai_keys").select("encrypted_key").eq("user_id", user_id).eq("provider", provider)\
            .execute().data
        enc = (data[0].get("encrypted_key") if data else None)
        if not enc:
            return None
        try:
            return self.keystore.decrypt(enc)
        except Exception:
            return None

    def delete_api_key(self, user_id: str, provider: str) -> bool:
        data = self._t("user_ai_keys").delete().eq("user_id", user_id).eq("provider", provider).execute().data
        return bool(data)

    # ---- preferências ----
    def get_ai_settings(self, user_id: str) -> Dict[str, Any]:
        data = self._t("ai_settings").select("*").eq("user_id", user_id).execute().data
        row = data[0] if data else {}
        out = dict(row)
        ov = out.get("agent_overrides")
        if not isinstance(ov, dict):
            out["agent_overrides"] = {}
        return out

    def save_ai_settings(self, user_id: str, data: Dict[str, Any]) -> None:
        payload = {"user_id": user_id, **{k: v for k, v in data.items() if k != "user_id"}}
        payload["updated_at"] = _now_iso()
        self._t("ai_settings").upsert(payload, on_conflict="user_id").execute()

    # ---- tarefas ----
    def list_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        rows = self._t("tasks").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
        for r in rows:
            for col in ("created_at", "due_date", "done_at"):
                r[col] = self._ms(r.get(col))
        return list(rows)

    def save_task(self, user_id: str, task: Dict[str, Any]) -> None:
        payload = {"user_id": user_id, **{k: v for k, v in task.items() if k not in ("user_id", "id")}}
        for col in ("created_at", "due_date", "done_at"):
            if col in payload:
                payload[col] = self._iso(payload.get(col))
        data = self._t("tasks").select("id").eq("id", task.get("id", "")).eq("user_id", user_id).execute().data
        if data:
            self._t("tasks").update(payload).eq("id", task["id"]).eq("user_id", user_id).execute()
        else:
            payload["id"] = task.get("id") or None
            self._t("tasks").insert(payload).execute()

    def delete_task(self, user_id: str, task_id: str) -> bool:
        data = self._t("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute().data
        return bool(data)

    # ---- atividade ----
    def log_activity(self, user_id: str, agent_id: str, operation: str, status: str,
                     provider: str = "", model: str = "", latency_ms: float = 0.0,
                     prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0) -> None:
        self._t("activity_logs").insert({
            "user_id": user_id, "agent_id": agent_id, "operation": operation, "status": status,
            "provider": provider, "model": model, "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": total_tokens, "created_at": _now_iso(),
        }).execute()

    def list_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._t("activity_logs").select("*").eq("user_id", user_id).order("created_at", desc=True)\
            .limit(limit).execute().data

    # ---- search ----
    def save_search(self, user_id: str, agent_id: str, query: str, provider: str,
                    results: List[Dict[str, Any]]) -> None:
        self._t("web_searches").insert({
            "user_id": user_id, "agent_id": agent_id, "query": query, "provider": provider,
            "results": results[:20], "created_at": _now_iso(),
        }).execute()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_data_store(root: Path, secret: bytes, user_id_salt: str = "") -> DataStore:
    """Supabase quando configurado; LocalStore como fallback sempre disponível."""
    url = os.getenv("SUPABASE_URL", "").strip()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    sb = SupabaseStore(url, service_key, secret)
    if sb.enabled:
        return sb
    return LocalStore(root, secret)