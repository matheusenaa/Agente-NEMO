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
    def append_message(self, user_id: str, conversation_id: str, role: str, content: str, meta: Optional[Dict[str, Any]] = None) -> bool: ...
    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]: ...
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool: ...
    def update_conversation(self, user_id: str, conversation_id: str, patch: Dict[str, Any]) -> bool: ...

    # ---- eventos (calendário) ----
    def list_events(self, user_id: str) -> List[Dict[str, Any]]: ...
    def save_event(self, user_id: str, event: Dict[str, Any]) -> None: ...
    def delete_event(self, user_id: str, event_id: str) -> bool: ...

    # ---- perfil do usuário ----
    def get_profile(self, user_id: str) -> Dict[str, Any]: ...
    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None: ...

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

    # ---- sincronização offline-first (missão §11-15) ----
    def get_changes_since(self, user_id: str, since_sync_version: int, stores: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]: ...
    def apply_sync_operations(self, user_id: str, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]: ...
    def get_sync_metadata(self, user_id: str) -> Dict[str, Any]: ...
    def update_sync_metadata(self, user_id: str, data: Dict[str, Any]) -> None: ...


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


def _replace_with_retry(source: Path, destination: Path, attempts: int = 6) -> None:
    """Substituição atômica com retry para travamento transitório no Windows.

    `Path.replace` falha com `PermissionError [WinError 5]` quando outro
    processo (antivírus, indexador, o próprio backend) mantém o arquivo de
    destino aberto. Uma falha única perdia a gravação silenciosamente.
    """
    last_error: Optional[BaseException] = None
    for attempt in range(attempts):
        try:
            os.replace(source, destination)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(0.05 * (2 ** attempt))
    raise last_error if last_error else OSError(f"Falha ao substituir {destination}")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _replace_with_retry(tmp, path)


def _item_timestamp(item: Dict[str, Any]) -> int:
    """Timestamp em ms de um registro, para o filtro incremental do sync.

    Nenhum writer local gravava `sync_version`, então o filtro antigo
    (`item.get("sync_version", 0) > since`) descartava TODAS as lojas e o
    sync/pull respondia "nada mudou" mesmo com dados novos no servidor.
    """
    raw = (
        item.get("updated_at") or item.get("created_at")
        or item.get("updatedAt") or item.get("createdAt") or 0
    )
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            return 0
    return 0


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
                       meta: Optional[Dict[str, Any]] = None) -> bool:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        appended = False
        for c in convs:
            if c.get("id") == conversation_id:
                c.setdefault("messages", []).append({
                    "role": role, "content": content, "meta": meta or {},
                    "created_at": _now_ms(),
                })
                c["updated_at"] = _now_ms()
                appended = True
                break
        if appended:
            _write_json(self._f(user_id, "conversations.json"), convs)
        # Antes escrevia o arquivo de volta sem gravar nada quando o id da
        # conversa não existia: a mensagem sumia sem erro nem log (§3/§31).
        return appended

    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        conv = self._find_conversation(user_id, conversation_id)
        return (conv or {}).get("messages", [])

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        remaining = [c for c in convs if c.get("id") != conversation_id]
        if len(remaining) == len(convs):
            return False
        _write_json(self._f(user_id, "conversations.json"), remaining)
        return True

    def update_conversation(self, user_id: str, conversation_id: str, patch: Dict[str, Any]) -> bool:
        convs = _read_json(self._f(user_id, "conversations.json"), [])
        for c in convs:
            if c.get("id") == conversation_id:
                c.update(patch)
                c["updated_at"] = _now_ms()
                _write_json(self._f(user_id, "conversations.json"), convs)
                return True
        return False

    # ---- eventos ----
    def list_events(self, user_id: str) -> List[Dict[str, Any]]:
        events = _read_json(self._f(user_id, "events.json"), [])
        events.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))
        return events

    def save_event(self, user_id: str, event: Dict[str, Any]) -> None:
        events = _read_json(self._f(user_id, "events.json"), [])
        events = [e for e in events if e.get("id") != event.get("id")]
        events.insert(0, event)
        _write_json(self._f(user_id, "events.json"), events[:500])

    def delete_event(self, user_id: str, event_id: str) -> bool:
        events = _read_json(self._f(user_id, "events.json"), [])
        remaining = [e for e in events if e.get("id") != event_id]
        if len(remaining) == len(events):
            return False
        _write_json(self._f(user_id, "events.json"), remaining)
        return True

    # ---- perfil do usuário ----
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        return _read_json(self._f(user_id, "profile.json"), {})

    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None:
        allowed = {k: data[k] for k in ("name", "email", "language", "avatar", "default_agent", "preferences") if k in data and data[k] is not None}
        profile = _read_json(self._f(user_id, "profile.json"), {})
        profile.update(allowed)
        profile["user_id"] = user_id
        _write_json(self._f(user_id, "profile.json"), profile)

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

    # ---- sincronização offline-first (missão §11-15) ----
    def _get_sync_metadata_file(self, user_id: str) -> Path:
        return self._f(user_id, "sync_metadata.json")

    def get_changes_since(self, user_id: str, since_sync_version: int, stores: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        # Os nomes reais dos arquivos: `activity_logs`/`web_searches` nunca
        # existiram como arquivo e `messages` vive dentro de `conversations.json`.
        # Ler `<store>.json` direto fazia 3 das 10 lojas voltarem sempre vazias.
        files = {
            "activity_logs": "activity.json",
            "web_searches": "searches.json",
        }
        all_stores = ["conversations", "memories", "tasks", "events", "ai_keys", "ai_settings", "profile", "activity_logs", "web_searches"]
        target_stores = stores if stores else all_stores
        changes: Dict[str, List[Dict[str, Any]]] = {}
        for store in target_stores:
            if store == "messages":
                # Mensagens chegam aninhadas em cada conversa.
                items = []
                for conv in _read_json(self._f(user_id, "conversations.json"), []):
                    for msg in conv.get("messages", []):
                        items.append({"conversation_id": conv.get("id"), **msg})
            else:
                items = _read_json(self._f(user_id, files.get(store, f"{store}.json")), [])
            if store == "ai_keys":
                items = [{"id": k, **v} for k, v in items.items()]
            elif store == "ai_settings" or store == "profile":
                items = [items] if items else []
            if not isinstance(items, list):
                continue
            filtered = [
                item for item in items
                if isinstance(item, dict)
                and _item_timestamp(item) > since_sync_version
            ]
            if filtered:
                changes[store] = filtered
        return changes

    def apply_sync_operations(self, user_id: str, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for op in operations:
            client_id = op.get("client_id")
            store = op.get("store")
            operation = op.get("operation")
            data = op.get("data", {})
            try:
                if store == "conversations":
                    if operation == "create":
                        conv = self.create_conversation(user_id, data.get("agent_id", "nemo"), data.get("title", "Nova conversa"))
                        results.append({"client_id": client_id, "status": "ok", "server_id": conv.get("id")})
                    elif operation == "update":
                        self.update_conversation(user_id, data["id"], data)
                        results.append({"client_id": client_id, "status": "ok", "server_id": data["id"]})
                    elif operation == "delete":
                        self.delete_conversation(user_id, data["id"])
                        results.append({"client_id": client_id, "status": "ok", "server_id": data["id"]})
                elif store == "memories":
                    if operation == "create":
                        mem = self.save_memory(user_id, data.get("agent_id", "nemo"), data.get("content", ""), data.get("kind", "obs"))
                        results.append({"client_id": client_id, "status": "ok", "server_id": mem.get("id")})
                    elif operation == "delete":
                        self.delete_memory(user_id, data["id"])
                        results.append({"client_id": client_id, "status": "ok", "server_id": data["id"]})
                elif store == "tasks":
                    if operation in ("create", "update"):
                        self.save_task(user_id, data)
                        results.append({"client_id": client_id, "status": "ok", "server_id": data.get("id")})
                    elif operation == "delete":
                        self.delete_task(user_id, data["id"])
                        results.append({"client_id": client_id, "status": "ok", "server_id": data["id"]})
                elif store == "events":
                    if operation in ("create", "update"):
                        self.save_event(user_id, data)
                        results.append({"client_id": client_id, "status": "ok", "server_id": data.get("id")})
                    elif operation == "delete":
                        self.delete_event(user_id, data["id"])
                        results.append({"client_id": client_id, "status": "ok", "server_id": data["id"]})
                elif store == "profile":
                    self.save_profile(user_id, data)
                    results.append({"client_id": client_id, "status": "ok", "server_id": "profile"})
                elif store == "ai_settings":
                    self.save_ai_settings(user_id, data)
                    results.append({"client_id": client_id, "status": "ok", "server_id": "ai_settings"})
                else:
                    results.append({"client_id": client_id, "status": "error", "error": f"Store {store} not supported"})
            except Exception as exc:
                results.append({"client_id": client_id, "status": "error", "error": str(exc)})
        return results

    def get_sync_metadata(self, user_id: str) -> Dict[str, Any]:
        return _read_json(self._get_sync_metadata_file(user_id), {"sync_version": 0})

    def update_sync_metadata(self, user_id: str, data: Dict[str, Any]) -> None:
        current = self.get_sync_metadata(user_id)
        current.update(data)
        _write_json(self._get_sync_metadata_file(user_id), current)


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
                       meta: Optional[Dict[str, Any]] = None) -> bool:
        try:
            self._t("messages").insert({
                "conversation_id": conversation_id, "user_id": user_id,
                "role": role, "content": content, "meta": meta or {},
                "created_at": _now_iso(),
            }).execute()
        except Exception:
            # Retorna False em vez de propagar: o chat já tem a resposta pronta e
            # o protocolo do DataStore é `bool` (o LocalStore também devolve).
            return False
        # `.eq("user_id", ...)`: sem isso o update tocava a conversa de outro
        # usuário que tivesse o mesmo id.
        self._t("conversations").update({"updated_at": _now_iso()})\
            .eq("id", conversation_id).eq("user_id", user_id).execute()
        return True

    def list_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        return self._t("messages").select("*").eq("conversation_id", conversation_id).eq("user_id", user_id)\
            .order("created_at").execute().data

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        owned = self._t("conversations").select("id").eq("id", conversation_id).eq("user_id", user_id).execute().data
        if not owned:
            return False
        self._t("messages").delete().eq("conversation_id", conversation_id).execute()
        self._t("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
        return True

    def update_conversation(self, user_id: str, conversation_id: str, patch: Dict[str, Any]) -> bool:
        owned = self._t("conversations").select("id").eq("id", conversation_id).eq("user_id", user_id).execute().data
        if not owned:
            return False
        payload = {k: v for k, v in patch.items() if k not in ("id", "user_id", "created_at", "message_count")}
        payload["updated_at"] = _now_iso()
        self._t("conversations").update(payload).eq("id", conversation_id).eq("user_id", user_id).execute()
        return True

    # ---- eventos (calendário) — tabela public.calendar_events ----
    _EVENT_COLUMNS = {
        "date": "event_date",
        "time": "event_time",
        "durationMin": "duration_min",
        "agentId": "agent_id",
        "remind": "remind_min",
        "createdAt": "created_at",
    }

    def list_events(self, user_id: str) -> List[Dict[str, Any]]:
        rows = self._t("calendar_events").select("*").eq("user_id", user_id).execute().data
        out: List[Dict[str, Any]] = []
        for r in rows:
            row = dict(r)
            row["date"] = row.pop("event_date", "") or ""
            row["time"] = row.pop("event_time", "") or "09:00"
            row["durationMin"] = row.pop("duration_min", 60)
            row["agentId"] = row.pop("agent_id", "nemo")
            row["remind"] = row.pop("remind_min", 15)
            row["createdAt"] = self._ms(row.pop("created_at", 0))
            row.setdefault("description", "")
            row.setdefault("category", "outro")
            out.append(row)
        out.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))
        return out

    def save_event(self, user_id: str, event: Dict[str, Any]) -> None:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "title": event.get("title") or "Sem título",
            "description": event.get("description") or "",
            "event_date": event.get("date") or None,
            "event_time": event.get("time") or "09:00",
            "duration_min": int(event.get("durationMin") or 60),
            "category": event.get("category") or "outro",
            "agent_id": event.get("agentId") or "nemo",
            "remind_min": int(event.get("remind") or 0),
        }
        if payload["event_date"] is None:
            raise ValueError("Evento sem data (date) não pode ser salvo.")
        payload["created_at"] = self._iso(event.get("createdAt") or _now_ms())
        if event.get("id"):
            owned = self._t("calendar_events").select("id").eq("id", event["id"]).eq("user_id", user_id).execute().data
            if owned:
                self._t("calendar_events").update(payload).eq("id", event["id"]).eq("user_id", user_id).execute()
                return
            payload["id"] = event["id"]
        self._t("calendar_events").upsert(payload, on_conflict="id").execute()

    def delete_event(self, user_id: str, event_id: str) -> bool:
        data = self._t("calendar_events").delete().eq("id", event_id).eq("user_id", user_id).execute().data
        return bool(data)

    # ---- perfil do usuário (profiles) ----
    _PROFILE_MAP = {"avatar": "avatar_url", "default_agent": None, "preferences": None}

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        data = self._t("profiles").select("*").eq("id", user_id).execute().data
        row = dict(data[0]) if data else {}
        out = {k: v for k, v in row.items() if k in ("id", "name", "email", "language", "role")}
        if "avatar_url" in row:
            out["avatar"] = row["avatar_url"]
        return out

    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None:
        payload: Dict[str, Any] = {"id": user_id, "updated_at": _now_iso()}
        for k in ("name", "email", "language"):
            if data.get(k) is not None:
                payload[k] = data[k]
        if data.get("avatar") is not None:
            payload["avatar_url"] = data["avatar"]
        self._t("profiles").upsert(payload, on_conflict="id").execute()

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
        for col in ("created_at", "updated_at", "due_date", "done_at"):
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

    # ---- sincronização offline-first (missão §11-15) ----
    def get_changes_since(self, user_id: str, since_sync_version: int, stores: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        if not self.enabled:
            return {}
        try:
            store_param = stores if stores else None
            res = self.client.rpc("get_changes_since", {
                "p_user_id": user_id,
                "p_since_sync_version": since_sync_version,
                "p_stores": store_param,
            }).execute()
            changes: Dict[str, List[Dict[str, Any]]] = {}
            for row in (res.data or []):
                store = row.get("store")
                if store:
                    changes.setdefault(store, []).append(row)
            return changes
        except Exception:
            return {}

    def apply_sync_operations(self, user_id: str, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.enabled:
            return [{"status": "error", "error": "Supabase not enabled"} for _ in operations]
        try:
            res = self.client.rpc("apply_sync_operations", {
                "p_user_id": user_id,
                "p_operations": operations,
            }).execute()
            return list(res.data or [])
        except Exception as exc:
            return [{"status": "error", "error": str(exc)} for _ in operations]

    def get_sync_metadata(self, user_id: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"sync_version": 0}
        try:
            data = self._t("sync_metadata").select("*").eq("user_id", user_id).execute().data
            return data[0] if data else {"sync_version": 0}
        except Exception:
            return {"sync_version": 0}

    def update_sync_metadata(self, user_id: str, data: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        payload = {"user_id": user_id, **data, "updated_at": _now_iso()}
        try:
            self._t("sync_metadata").upsert(payload, on_conflict="user_id").execute()
        except Exception:
            pass


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