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
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.referer = referer or os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000")
        self.app_title = app_title or os.getenv("OPENROUTER_APP_TITLE", "NEMO AI Studio")
        self.base_url = base_url

        self.default_headers = {
            "HTTP-Referer": self.referer,
            "X-Title": self.app_title,
        }

        # Inicializa cliente OpenAI síncrono configurado para o OpenRouter
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key if self.api_key else "dummy_key_for_init",
            default_headers=self.default_headers,
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
                    "error": f"Erro de validação da chave (HTTP {resp.status_code}): {resp.text}"
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
        if fallback_slugs:
            for fb in fallback_slugs:
                if fb not in slugs_to_try:
                    slugs_to_try.append(fb)

        last_error = None

        for idx, current_slug in enumerate(slugs_to_try):
            is_fallback = (idx > 0)
            start_time = time.perf_counter()

            try:
                response = self.client.chat.completions.create(
                    model=current_slug,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000

                choice = response.choices[0] if response.choices else None
                content = choice.message.content.strip() if choice and choice.message.content else ""
                finish_reason = choice.finish_reason if choice else None

                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                total_tokens = usage.total_tokens if usage else 0

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

            except NotFoundError as e:
                # Modelo não encontrado: tenta o próximo fallback
                last_error = f"Modelo não encontrado ({current_slug}): {str(e)}"
                continue
            except APIError as e:
                # Erro de API: verifica se é erro de modelo descontinuado ou sem rota
                error_str = str(e)
                if "not found" in error_str.lower() or "no endpoints" in error_str.lower():
                    last_error = f"Modelo sem rota disponível ({current_slug}): {error_str}"
                    continue
                else:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    return CompletionResult(
                        success=False,
                        content="",
                        model_used=current_slug,
                        original_model=model,
                        is_fallback=is_fallback,
                        latency_ms=round(latency_ms, 2),
                        error_message=f"Erro da API OpenRouter ({type(e).__name__}): {error_str}"
                    )
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                return CompletionResult(
                    success=False,
                    content="",
                    model_used=current_slug,
                    original_model=model,
                    is_fallback=is_fallback,
                    latency_ms=round(latency_ms, 2),
                    error_message=f"Exceção inesperada ({type(e).__name__}): {str(e)}"
                )

        # Se todos os slugs falharem
        return CompletionResult(
            success=False,
            content="",
            model_used=model,
            original_model=model,
            is_fallback=False,
            latency_ms=0.0,
            error_message=last_error or "Todos os slugs tentados falharam."
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
