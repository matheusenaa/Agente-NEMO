"""
Cliente modular e resiliente para comunicação com a API do OpenRouter (https://openrouter.ai/).
Suporta SDK OpenAI v1, cabeçalhos obrigatórios (HTTP-Referer, X-Title),
verificação de autenticação, resolução dinâmica de slugs e fallbacks automáticos.
"""

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import requests
from openai import OpenAI, AsyncOpenAI, APIError, NotFoundError

from models_config import ModelInfo, OPENROUTER_MODELS

# Carrega variáveis de ambiente do .env
load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

@dataclass
class CompletionResult:
    success: bool
    content: str
    model_used: str
    original_model: str
    is_fallback: bool
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_message: Optional[str] = None
    finish_reason: Optional[str] = None

class OpenRouterClient:
    """Cliente modular para a API OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        referer: Optional[str] = None,
        app_title: Optional[str] = None,
        base_url: str = OPENROUTER_BASE_URL,
        request_timeout: float = 45.0,
    ):
        # Chave explícita vazia ("") significa SEM chave; só usa o .env quando NADA é passado.
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip() if api_key is None else api_key.strip()
        self.referer = referer or os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000")
        self.app_title = app_title or os.getenv("OPENROUTER_APP_TITLE", "NEMO AI Studio")
        self.base_url = base_url
        self.request_timeout = max(1.0, min(float(request_timeout), 300.0))

        self.default_headers = {
            "HTTP-Referer": self.referer,
            "X-Title": self.app_title,
        }

        # Inicializa cliente OpenAI síncrono configurado para o OpenRouter
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key if self.api_key else "dummy_key_for_init",
            default_headers=self.default_headers,
            timeout=self.request_timeout,
            max_retries=0,
        )

        # Cache do catálogo de modelos ativos do OpenRouter
        self._live_models_cache: Optional[List[str]] = None

    def has_valid_key_format(self) -> bool:
        """Verifica se a chave não está vazia nem é o placeholder padrão."""
        if not self.api_key:
            return False
        if self.api_key in ["sua_chave_aqui", "your_key_here", "sk-or-v1-..."]:
            return False
        return len(self.api_key) > 10

    def check_auth(self) -> Dict[str, Any]:
        """
        Valida a chave da API junto ao endpoint https://openrouter.ai/api/v1/auth/key.
        Retorna informações sobre limite de créditos, uso e status da conta.
        """
        if not self.has_valid_key_format():
            return {
                "valid": False,
                "error": "A variável OPENROUTER_API_KEY não foi configurada ou ainda contém o valor padrão."
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            **self.default_headers
        }

        try:
            resp = requests.get(f"{self.base_url}/auth/key", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "valid": True,
                    "label": data.get("label"),
                    "usage": data.get("usage"),
                    "limit": data.get("limit"),
                    "is_free_tier": data.get("is_free_tier"),
                    "rate_limit": data.get("rate_limit"),
                }
            elif resp.status_code == 401:
                return {
                    "valid": False,
                    "error": "Chave de API inválida ou expirada (HTTP 401 Unauthorized)."
                }
            else:
                return {
                    "valid": False,
                    "error": f"Erro de validação da chave (HTTP {resp.status_code})."
                }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Falha de conexão com OpenRouter: {str(e)}"
            }

    def get_live_models(self, force_refresh: bool = False) -> List[str]:
        """Obtém os IDs de todos os modelos ativos atualmente no OpenRouter."""
        if self._live_models_cache is not None and not force_refresh:
            return self._live_models_cache

        try:
            resp = requests.get(f"{self.base_url}/models", timeout=12)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                self._live_models_cache = [m["id"] for m in data if "id" in m]
                return self._live_models_cache
        except Exception:
            pass

        return []

    def resolve_model_slug(self, model_info: ModelInfo) -> Tuple[str, bool]:
        """
        Determina o melhor slug ativo para o modelo solicitado.
        Retorna (slug_escolhido, is_fallback).
        """
        live_models = self.get_live_models()
        if not live_models:
            # Se não conseguir obter catálogo, tenta o primário
            return model_info.primary_slug, False

        # Verifica se o primário existe diretamente no catálogo ativo
        if model_info.primary_slug in live_models:
            return model_info.primary_slug, False

        # Procura nos fallbacks definidos
        for fallback in model_info.fallback_slugs:
            if fallback in live_models:
                return fallback, True

        # Se nenhum fallback exato bater, tenta encontrar correspondência parcial
        keyword = model_info.id.split("-")[0]
        for live_id in live_models:
            if keyword in live_id and model_info.provider.lower() in live_id:
                return live_id, True

        # Último caso: envia o primário mesmo assim (pode haver redirecionamento no servidor)
        return model_info.primary_slug, False

    @staticmethod
    def _error_status(error: BaseException) -> Optional[int]:
        status = getattr(error, "status_code", None)
        if not isinstance(status, int):
            response = getattr(error, "response", None)
            status = getattr(response, "status_code", None)
        return status if isinstance(status, int) else None

    @classmethod
    def _is_retryable_error(cls, error: BaseException) -> bool:
        status = cls._error_status(error)
        if status is not None:
            return status in {408, 425, 429} or status >= 500
        message = str(error).lower()
        markers = (
            "connection", "timeout", "timed out", "temporarily", "overloaded",
            "rate limit", "too many requests", "429", "service unavailable",
            "bad gateway", "internal server", "no endpoints", "model not found",
            "not found", "max retries", "network", "unreachable", "ssl", "tls",
        )
        return any(marker in message for marker in markers)

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150,
        fallback_slugs: Optional[List[str]] = None,
    ) -> CompletionResult:
        """
        Envia uma requisição de chat completion com suporte a retry, fallbacks e medição de latência.
        """
        slugs_to_try = [model]
        for fallback_slug in fallback_slugs or []:
            if fallback_slug and fallback_slug not in slugs_to_try:
                slugs_to_try.append(fallback_slug)

        temperature = max(0.0, min(float(temperature), 2.0))
        max_tokens = max(1, min(int(max_tokens), 4000))
        deadline = time.monotonic() + self.request_timeout
        last_error: Optional[str] = None
        last_slug = model
        total_started = time.perf_counter()

        for idx, current_slug in enumerate(slugs_to_try):
            is_fallback = idx > 0
            last_slug = current_slug
            if time.monotonic() >= deadline and idx > 0:
                last_error = "Tempo limite total do fallback excedido."
                break

            start_time = time.perf_counter()
            remaining_timeout = max(1.0, deadline - time.monotonic())
            try:
                response = self.client.chat.completions.create(
                    model=current_slug,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=remaining_timeout,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000
                choice = response.choices[0] if response.choices else None
                content = str(choice.message.content or "").strip() if choice else ""
                finish_reason = choice.finish_reason if choice else None

                usage = response.usage
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0

                return CompletionResult(
                    success=True,
                    content=content,
                    model_used=current_slug,
                    original_model=model,
                    is_fallback=is_fallback,
                    latency_ms=round(latency_ms, 2),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    finish_reason=finish_reason,
                )

            except NotFoundError as exc:
                last_error = f"Modelo não encontrado ({current_slug}): {str(exc)}"
                continue
            except APIError as exc:
                error_message = str(exc)
                if self._is_retryable_error(exc):
                    last_error = f"Falha transitória ({current_slug}): {error_message}"
                    continue
                latency_ms = (time.perf_counter() - start_time) * 1000
                return CompletionResult(
                    success=False,
                    content="",
                    model_used=current_slug,
                    original_model=model,
                    is_fallback=is_fallback,
                    latency_ms=round(latency_ms, 2),
                    error_message=f"Erro da API OpenRouter ({type(exc).__name__}): {error_message}",
                )
            except Exception as exc:
                if self._is_retryable_error(exc):
                    last_error = f"Falha transitória ({current_slug}): {str(exc)}"
                    continue
                latency_ms = (time.perf_counter() - start_time) * 1000
                return CompletionResult(
                    success=False,
                    content="",
                    model_used=current_slug,
                    original_model=model,
                    is_fallback=is_fallback,
                    latency_ms=round(latency_ms, 2),
                    error_message=f"Exceção inesperada ({type(exc).__name__}): {str(exc)}",
                )

        total_latency_ms = (time.perf_counter() - total_started) * 1000
        return CompletionResult(
            success=False,
            content="",
            model_used=last_slug,
            original_model=model,
            is_fallback=len(slugs_to_try) > 1,
            latency_ms=round(total_latency_ms, 2),
            error_message=last_error or "Todos os slugs tentados falharam.",
        )

    def test_single_model(
        self,
        model_info: ModelInfo,
        prompt: str = "Responda apenas 'OK' e o seu nome de modelo",
        temperature: float = 0.2,
        max_tokens: int = 100,
    ) -> CompletionResult:
        """Testa um modelo específico usando o prompt padrão ou customizado."""
        # Pré-resolve slug se primário estiver desatualizado
        resolved_slug, was_pre_resolved = self.resolve_model_slug(model_info)

        # Prepara lista de fallbacks incluindo o slug original e os demais
        fallbacks = [s for s in [resolved_slug] + model_info.fallback_slugs if s != model_info.primary_slug]

        messages = [
            {"role": "user", "content": prompt}
        ]

        # Inicia teste pelo primário se ele for ativo, ou pelo resolved_slug
        start_slug = resolved_slug if was_pre_resolved else model_info.primary_slug
        remaining_fallbacks = [s for s in [model_info.primary_slug] + fallbacks if s != start_slug]

        res = self.chat_completion(
            model=start_slug,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_slugs=remaining_fallbacks,
        )

        if was_pre_resolved and res.model_used != model_info.primary_slug:
            res.is_fallback = True

        return res
