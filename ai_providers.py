"""
NEMO — Camada abstrata de provedores de IA (missão: Supabase + Gemini + Groq + IA do usuário).

Arquitetura:
    AIProviderService
    ├── GeminiProvider        (API REST do Google Gemini)
    ├── GroqProvider          (API OpenAI-compatível do Groq)
    ├── OpenAIProvider        (OpenAI / base compatível configurável)
    └── OpenRouterProvider    (cliente OpenRouter já existente)

O restante do sistema conversa APENAS com AIProviderService. Assim é possível
adicionar novos provedores (Anthropic, modelos locais etc.) sem reconstruir
os agentes. Nenhuma API Key é colocada no frontend nem nos logs: elas vêm de
variáveis de ambiente (sistema) ou do cofre criptografado por usuário.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

load_dotenv()

# ---------------------------------------------------------------------------
# Erros e resultado comum
# ---------------------------------------------------------------------------


class AIError(Exception):
    """Erro controlado da camada de IA (mensagem amigável, sem secrets)."""

    def __init__(self, message: str, status: int = 500, provider: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.provider = provider


@dataclass
class CompletionResult:
    success: bool
    content: str
    model_used: str
    provider: str
    original_model: str
    is_fallback: bool = False
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None
    finish_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Catálogo de modelos por provedor (listas sensatas; o provedor valida na hora)
# ---------------------------------------------------------------------------

GEMINI_MODELS: List[str] = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-pro-latest",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

GROQ_MODELS: List[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

OPENAI_MODELS: List[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "o3-mini",
]

PROVIDER_META: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "name": "Google Gemini",
        "icon": "✨",
        "models": GEMINI_MODELS,
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    },
    "groq": {
        "name": "Groq",
        "icon": "⚡",
        "models": GROQ_MODELS,
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "openai": {
        "name": "OpenAI",
        "icon": "🧠",
        "models": OPENAI_MODELS,
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
    },
    "openrouter": {
        "name": "OpenRouter",
        "icon": "🌐",
        "models": [],
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
    },
}


def _provider_meta(provider: str) -> Dict[str, Any]:
    return PROVIDER_META.get(provider or "", PROVIDER_META["openrouter"])


def _normalize_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Normaliza a lista de mensagens para o formato OpenAI-style (role/content)."""
    out: List[Dict[str, str]] = []
    for m in messages:
        role = (m.get("role") or "").strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role in ("user", "assistant", "system"):
            out.append({"role": role, "content": content})
    return out


# ---------------------------------------------------------------------------
# Provedores
# ---------------------------------------------------------------------------


class GeminiProvider:
    """Provedor Google Gemini via REST (sem SDK obrigatório e sem key no frontend)."""

    def __init__(self, api_key: str):
        if not api_key or len(api_key) < 10:
            raise AIError("Chave do Gemini não configurada.", status=400, provider="gemini")
        self.api_key = api_key
        self.base_url = PROVIDER_META["gemini"]["base_url"]

    def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> CompletionResult:
        msgs = _normalize_messages(messages)
        system_parts: List[Dict[str, str]] = []
        contents: List[Dict[str, Any]] = []
        for m in msgs:
            if m["role"] == "system":
                system_parts.append({"text": m["content"]})
            else:
                role = "user" if m["role"] != "assistant" else "model"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Olá."}]}]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max(1, max_tokens)},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        started = time.perf_counter()
        try:
            resp = requests.post(
                f"{self.base_url}/models/{model}:generateContent",
                params={"key": self.api_key},
                json=payload,
                timeout=120,
            )
            latency = round((time.perf_counter() - started) * 1000, 2)
        except requests.RequestException as exc:
            latency = round((time.perf_counter() - started) * 1000, 2)
            return CompletionResult(
                success=False, content="", model_used=model, provider="gemini", original_model=model,
                latency_ms=latency, error_message=f"Falha de conexão com Gemini: {exc}",
            )
        if resp.status_code == 200:
            data = resp.json()
            try:
                candidate = data["candidates"][0]
                parts = candidate.get("content", {}).get("parts", [])
                content = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                finish = candidate.get("finishReason")
            except (KeyError, IndexError):
                content, finish = "", None
            usage = data.get("usageMetadata") or {}
            return CompletionResult(
                success=True, content=content, model_used=model, provider="gemini", original_model=model,
                latency_ms=latency,
                prompt_tokens=int(usage.get("promptTokenCount", 0) or 0),
                completion_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
                total_tokens=int(usage.get("totalTokenCount", 0) or 0),
                finish_reason=finish,
            )
        return self._error(resp, model, latency)

    def _error(self, resp: requests.Response, model: str, latency: float) -> CompletionResult:
        err = ""
        try:
            err = str(resp.json())
        except Exception:
            err = resp.text[:300]
        status = resp.status_code
        if status == 401 or status == 403:
            msg = "Gemini: API Key inválida ou sem autorização."
        elif status == 404:
            msg = f"Gemini: modelo '{model}' não encontrado ou indisponível."
        else:
            msg = f"Gemini: erro HTTP {status}."
        return CompletionResult(
            success=False, content="", model_used=model, provider="gemini", original_model=model,
            latency_ms=latency, error_message=f"{msg} :: {err[:160]}",
        )


class OpenAICompatibleProvider:
    """Provedor OpenAI-compatível (Groq, OpenAI, ou base_url customizada)."""

    def __init__(self, provider: str, api_key: str, base_url: Optional[str] = None):
        if not api_key or len(api_key) < 5:
            raise AIError(f"Chave do {_provider_meta(provider)['name']} não configurada.", status=400, provider=provider)
        self.provider = provider
        self.api_key = api_key
        self.base_url = (base_url or _provider_meta(provider)["base_url"]).rstrip("/")

    def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 900,
    ) -> CompletionResult:
        msgs = _normalize_messages(messages)
        payload = {
            "model": model,
            "messages": msgs or [{"role": "user", "content": "Olá."}],
            "temperature": temperature,
            "max_tokens": max(1, max_tokens),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        started = time.perf_counter()
        try:
            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=120)
            latency = round((time.perf_counter() - started) * 1000, 2)
        except requests.RequestException as exc:
            latency = round((time.perf_counter() - started) * 1000, 2)
            return CompletionResult(
                success=False, content="", model_used=model, provider=self.provider, original_model=model,
                latency_ms=latency, error_message=f"Falha de conexão com {self.provider}: {exc}",
            )
        if resp.status_code == 200:
            data = resp.json()
            try:
                choice = data["choices"][0]
                content = (choice.get("message") or {}).get("content") or ""
                finish = choice.get("finish_reason")
            except (KeyError, IndexError):
                content, finish = "", None
            usage = data.get("usage") or {}
            return CompletionResult(
                success=True, content=content, model_used=model, provider=self.provider, original_model=model,
                latency_ms=latency,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                total_tokens=int(usage.get("total_tokens", 0) or 0),
                finish_reason=finish,
            )
        return self._error(resp, model, latency)

    def _error(self, resp: requests.Response, model: str, latency: float) -> CompletionResult:
        err = ""
        try:
            err = str(resp.json())
        except Exception:
            err = resp.text[:300]
        status = resp.status_code
        name = _provider_meta(self.provider)["name"]
        if status in (401, 403):
            msg = f"{name}: API Key inválida ou sem autorização."
        elif status == 404:
            msg = f"{name}: modelo '{model}' não encontrado ou indisponível."
        else:
            msg = f"{name}: erro HTTP {status}."
        return CompletionResult(
            success=False, content="", model_used=model, provider=self.provider, original_model=model,
            latency_ms=latency, error_message=f"{msg} :: {err[:160]}",
        )


class GroqProvider(OpenAICompatibleProvider):
    """Provedor Groq (OpenAI-compatible)."""

    def __init__(self, api_key: str):
        super().__init__("groq", api_key)


class OpenAIProvider(OpenAICompatibleProvider):
    """Provedor OpenAI (chave do usuário ou do sistema)."""

    def __init__(self, api_key: str):
        super().__init__("openai", api_key)


class OpenRouterProvider:
    """Wrapper da camada OpenRouter já existente."""

    def __init__(self, api_key: str):
        from openrouter_client import OpenRouterClient
        self.client = OpenRouterClient(api_key=api_key or None)

    def complete(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 900,
        fallback_slugs: Optional[List[str]] = None,
    ) -> CompletionResult:
        res = self.client.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_slugs=fallback_slugs,
        )
        return CompletionResult(
            success=res.success,
            content=res.content,
            model_used=res.model_used,
            provider="openrouter",
            original_model=model,
            is_fallback=res.is_fallback,
            latency_ms=res.latency_ms,
            prompt_tokens=res.prompt_tokens,
            completion_tokens=res.completion_tokens,
            total_tokens=res.total_tokens,
            error_message=res.error_message,
            finish_reason=res.finish_reason,
        )


# ---------------------------------------------------------------------------
# Serviço (dispatcher)
# ---------------------------------------------------------------------------

MAX_FALLBACKS = 3  # limite de tentativas — sem fallback infinito (missão §33)

TEST_PROMPT = "Responda apenas OK com o nome do seu modelo."


class AIProviderService:
    """Dispatcher de provedores. Lê chaves de sistema (.env) e aceita chaves de usuário."""

    def __init__(self):
        load_dotenv()
        self.system_keys: Dict[str, str] = {
            "gemini": os.getenv("GEMINI_API_KEY", "").strip(),
            "groq": os.getenv("GROQ_API_KEY", "").strip(),
            "openai": os.getenv("OPENAI_API_KEY", "").strip(),
            "openrouter": os.getenv("OPENROUTER_API_KEY", "").strip(),
        }
        self._openrouter: Optional[OpenRouterProvider] = None

    # ------------------------------------------------------------------
    # Introspectão
    # ------------------------------------------------------------------
    def has_system_key(self, provider: str) -> bool:
        key = self.system_keys.get(provider or "", "")
        if not key:
            return False
        return key not in ("sua_chave_aqui", "your_key_here") and len(key) > 10

    def provider_catalog(self) -> List[Dict[str, Any]]:
        """Catálogo público de provedores (sem segredos)."""
        out: List[Dict[str, Any]] = []
        for pid, meta in PROVIDER_META.items():
            models = list(meta["models"]) if meta["models"] else [m.id for m in self._openrouter_models()]
            out.append({
                "id": pid,
                "name": meta["name"],
                "icon": meta["icon"],
                "configured": self.has_system_key(pid),
                "models": models,
            })
        return out

    def _openrouter_models(self):
        try:
            from models_config import get_all_models
            return get_all_models()
        except Exception:
            return []

    def default_provider(self) -> str:
        return os.getenv("NEMO_AI_PROVIDER", "openrouter") or "openrouter"

    def default_provider_model(self) -> str:
        provider = self.default_provider()
        key = self.system_keys.get(provider, "")
        if provider == "gemini":
            return GEMINI_MODELS[0] if GEMINI_MODELS else "gemini-flash-latest"
        if provider == "groq":
            return GROQ_MODELS[0] if GROQ_MODELS else "openai/gpt-oss-20b"
        if provider == "openai":
            return OPENAI_MODELS[0] if OPENAI_MODELS else "gpt-4o-mini"
        return OPENROUTER_MODELS[0] if OPENROUTER_MODELS else (key or "openrouter/auto")

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------
    def _build_provider(self, provider: str, api_key: Optional[str]) -> Any:
        key = (api_key or "").strip() if api_key else self.system_keys.get(provider, "")
        if provider == "gemini":
            return GeminiProvider(key)
        if provider == "groq":
            return GroqProvider(key)
        if provider == "openai":
            return OpenAIProvider(key)
        if provider == "openrouter":
            if self._openrouter is None:
                self._openrouter = OpenRouterProvider(key or None)
            return self._openrouter
        raise AIError("Provedor de IA desconhecido.", status=400, provider=provider)

    def complete(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 900,
        api_key: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        fallback_slugs: Optional[List[str]] = None,
    ) -> CompletionResult:
        """Tenta o provedor principal e, em caso de falha, o próximo configurado (limitado)."""
        chain: List[str] = []
        for p in [provider] + (fallback_providers or []):
            if p and p not in chain:
                chain.append(p)
            if len(chain) >= MAX_FALLBACKS:
                break

        last: Optional[CompletionResult] = None
        for idx, pid in enumerate(chain):
            key = api_key if api_key else self.system_keys.get(pid, "")
            if not key:
                last = CompletionResult(
                    success=False, content="", model_used=model, provider=pid, original_model=model,
                    is_fallback=idx > 0,
                    error_message=f"{_provider_meta(pid)['name']}: chave não configurada.",
                )
                continue
            try:
                prov = self._build_provider(pid, key)
                if pid == "openrouter":
                    res = prov.complete(model, messages, temperature, max_tokens, fallback_slugs=fallback_slugs)
                else:
                    res = prov.complete(model, messages, temperature, max_tokens)
            except AIError as exc:
                last = CompletionResult(
                    success=False, content="", model_used=model, provider=pid, original_model=model,
                    is_fallback=idx > 0, error_message=exc.message,
                )
                continue
            except Exception as exc:  # pragma: no cover
                last = CompletionResult(
                    success=False, content="", model_used=model, provider=pid, original_model=model,
                    is_fallback=idx > 0, error_message=f"{_provider_meta(pid)['name']}: {type(exc).__name__}",
                )
                continue
            if res.success:
                res.is_fallback = idx > 0 or (pid == "openrouter" and res.is_fallback)
                return res
            last = res
        return last or CompletionResult(
            success=False, content="", model_used=model, provider=provider, original_model=model,
            error_message="Nenhum provedor de IA disponível.",
        )

    def test_key(self, provider: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Testa uma chave (do usuário ou do sistema) sem persistir nem expor."""
        meta = _provider_meta(provider)
        models = model or (meta["models"][0] if meta["models"] else "deepseek/deepseek-chat")
        try:
            prov = self._build_provider(provider, api_key)
            res = prov.complete(models, [{"role": "user", "content": TEST_PROMPT}], 0.2, 50)
        except AIError as exc:
            return {"ok": False, "provider": provider, "message": exc.message, "error": exc.message}
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "provider": provider, "message": f"Não foi possível testar: {type(exc).__name__}"}
        if res.success:
            return {
                "ok": True,
                "provider": provider,
                "model": res.model_used,
                "message": "✓ Conexão funcionando.",
                "latency_ms": res.latency_ms,
            }
        if "inválida" in (res.error_message or "") or "Key" in (res.error_message or ""):
            return {"ok": False, "provider": provider, "message": "✕ Não foi possível autenticar."}
        return {"ok": False, "provider": provider, "message": "✕ Não foi possível autenticar.", "detail": (res.error_message or "")[:200]}