"""
Definição dos 10 principais modelos para integração via OpenRouter.
Inclui slugs oficiais primários e fallbacks ativos para máxima resiliência.

Os slugs foram conferidos contra o catálogo vivo de `/api/v1/models`.
Slug morto não é inofensivo: o OpenRouter responde 400 "not a valid model ID"
e esse erro passa a ser a ÚLTIMA mensagem da cadeia de fallback, mascarando
a causa real (ex.: 402 sem crédito). `test_models_config.py` trava isso.
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
        name="Claude Sonnet",
        provider="Anthropic",
        primary_slug="anthropic/claude-sonnet-4.6",
        fallback_slugs=[
            "anthropic/claude-sonnet-4.5",
            "~anthropic/claude-sonnet-latest",
            "anthropic/claude-sonnet-4",
            "anthropic/claude-haiku-4.5"
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
        name="Gemini Flash",
        provider="Google",
        primary_slug="google/gemini-2.5-flash",
        fallback_slugs=[
            "google/gemini-2.5-flash-lite",
            "google/gemini-3.5-flash",
            "~google/gemini-flash-latest"
        ],
        description="Modelo ultrarrápido e econômico do Google com janela estendida."
    ),
    ModelInfo(
        id="gemini-pro-1.5",
        name="Gemini Pro",
        provider="Google",
        primary_slug="google/gemini-2.5-pro",
        fallback_slugs=[
            "google/gemini-2.5-flash",
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
        primary_slug="meta-llama/llama-3.3-70b-instruct",
        fallback_slugs=[
            "meta-llama/llama-3.1-70b-instruct",
            "nousresearch/hermes-3-llama-3.1-405b"
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
        fallback_slugs=[
            "deepseek/deepseek-chat-v3.1",
            "qwen/qwen-2.5-coder-32b-instruct"
        ],
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
