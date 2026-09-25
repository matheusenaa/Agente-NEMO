"""
Definição dos 10 principais modelos para integração via OpenRouter.
Inclui slugs oficiais primários e fallbacks ativos para máxima resiliência.
"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    primary_slug: str
    fallback_slugs: List[str] = field(default_factory=list)
    description: str = ""

# Lista dos 10 principais modelos solicitados com fallbacks inteligentes
OPENROUTER_MODELS: List[ModelInfo] = [
    ModelInfo(
        id="claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="Anthropic",
        primary_slug="anthropic/claude-3.5-sonnet",
        fallback_slugs=[
            "anthropic/claude-sonnet-4",
            "anthropic/claude-sonnet-4.5",
            "~anthropic/claude-sonnet-latest",
            "anthropic/claude-3-haiku"
        ],
        description="Modelo de ponta da Anthropic para raciocínio, visão e código."
    ),
    ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        primary_slug="openai/gpt-4o",
        fallback_slugs=["openai/gpt-4o-2024-08-06", "openai/gpt-4o-mini"],
        description="Modelo multimodal flagship da OpenAI com alta velocidade e inteligência."
    ),
    ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        primary_slug="openai/gpt-4o-mini",
        fallback_slugs=["openai/gpt-4o"],
        description="Modelo compacto de alta performance e baixo custo da OpenAI."
    ),
    ModelInfo(
        id="gemini-flash-1.5",
        name="Gemini Flash 1.5",
        provider="Google",
        primary_slug="google/gemini-flash-1.5",
        fallback_slugs=[
            "google/gemini-2.5-flash",
            "google/gemini-3.5-flash",
            "~google/gemini-flash-latest"
        ],
        description="Modelo ultrarrápido e econômico do Google com janela estendida."
    ),
    ModelInfo(
        id="gemini-pro-1.5",
        name="Gemini Pro 1.5",
        provider="Google",
        primary_slug="google/gemini-pro-1.5",
        fallback_slugs=[
            "google/gemini-2.5-pro",
            "~google/gemini-pro-latest"
        ],
        description="Modelo avançado de raciocínio complexo e multimodal do Google."
    ),
    ModelInfo(
        id="llama-3.1-70b-instruct",
        name="Llama 3.1 70B Instruct",
        provider="Meta",
        primary_slug="meta-llama/llama-3.1-70b-instruct",
        fallback_slugs=["meta-llama/llama-3.3-70b-instruct"],
        description="Modelo de pesos abertos de 70B parâmetros de alta precisão da Meta."
    ),
    ModelInfo(
        id="llama-3.1-405b-instruct",
        name="Llama 3.1 405B Instruct",
        provider="Meta",
        primary_slug="meta-llama/llama-3.1-405b-instruct",
        fallback_slugs=[
            "nousresearch/hermes-3-llama-3.1-405b",
            "meta-llama/llama-3.3-70b-instruct"
        ],
        description="O maior e mais capaz modelo open-source da Meta (405B parâmetros)."
    ),
    ModelInfo(
        id="mixtral-8x22b-instruct",
        name="Mixtral 8x22B Instruct",
        provider="Mistral",
        primary_slug="mistralai/mixtral-8x22b-instruct",
        fallback_slugs=["mistralai/mistral-large-2407"],
        description="MoE (Mixture of Experts) de alta capacidade da Mistral AI."
    ),
    ModelInfo(
        id="deepseek-chat",
        name="DeepSeek Chat / Coder",
        provider="DeepSeek",
        primary_slug="deepseek/deepseek-chat",
        fallback_slugs=["deepseek/deepseek-coder"],
        description="Modelo de alto desempenho e raciocínio técnico da DeepSeek."
    ),
    ModelInfo(
        id="qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B Instruct",
        provider="Qwen (Alibaba)",
        primary_slug="qwen/qwen-2.5-72b-instruct",
        fallback_slugs=["qwen/qwen-2.5-coder-32b-instruct"],
        description="Modelo open-weights líder mundial em código e matemática da Alibaba."
    )
]

def get_model_by_id(model_id: str) -> Optional[ModelInfo]:
    for model in OPENROUTER_MODELS:
        if model_id == model.id or model_id == model.primary_slug or model_id in model.fallback_slugs:
            return model
    return None

def get_all_models() -> List[ModelInfo]:
    return OPENROUTER_MODELS
