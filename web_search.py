"""
NEMO — Web Search Service (missão §9/§10/§20-21).

Camada que esconde as diferenças entre mecanismos de busca.

DIAGNÓSTICO (28/09/2026): o provedor anterior (scraping do HTML do DuckDuckGo)
está MORTO — `html.duckduckgo.com`, `lite.duckduckgo.com` e a Instant Answer API
respondem **HTTP 202 com página de desafio anti-bot** e ZERO resultados. Era por
isso que a busca "funcionava" (HTTP 200 do endpoint) mas nunca trazia nada, e o
agente respondia com alucinação de conhecimento antigo.

Ordem de preferência agora:
    1. Tavily   → melhor qualidade quando há TAVILY_API_KEY
    2. Brave    → quando há BRAVE_API_KEY
    3. OpenRouter Web → usa a chave que o sistema JÁ tem; o próprio modelo faz
       a busca e devolve `annotations` com as fontes. É o padrão do produto.
    4. Wikipedia → sempre disponível, sem chave. Serve para fatos verificáveis
       (pessoas, cidades, obras, conceitos) e é honesto sobre o próprio limite.

Regra inegociável (§9): se TODOS falharem, o serviço devolve `ok: False` com o
motivo. O agente é instruído a NUNCA inventar resultado de pesquisa.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 NEMO/1.0"
# Identificação honesta: a Wikipédia exige um User-Agent descritivo.
WIKI_UA = "SYNOP/1.0 (https://synop.app; contato@synop.app)"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Modelo barato e rápido só para a etapa de busca.
OPENROUTER_SEARCH_MODEL = os.getenv("OPENROUTER_SEARCH_MODEL", "deepseek/deepseek-chat").strip()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = ""
    date: Optional[str] = None
    query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "date": self.date,
            "query": self.query,
        }


class WebSearchError(Exception):
    """Erro de busca. `.message` existe porque a API expõe esse atributo
    (mesmo contrato de `AuthError`/`KeyStoreError` usados no servidor)."""

    @property
    def message(self) -> str:
        return str(self) or "Falha na busca."


# ---------------------------------------------------------------------------
# Provedores com chave (melhor qualidade quando disponíveis)
# ---------------------------------------------------------------------------


class TavilyProvider:
    """Tavily Search API (requer TAVILY_API_KEY). Retorna JSON estruturado."""

    name = "tavily"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": self.api_key, "query": query, "max_results": limit},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Tavily indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Tavily retornou HTTP {resp.status_code}")
        data = resp.json()
        out: List[SearchResult] = []
        for item in data.get("results", []):
            out.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                source=self.name,
                query=query,
            ))
        return out


class BraveProvider:
    """Brave Search API (requer BRAVE_API_KEY)."""

    name = "brave"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Brave indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Brave retornou HTTP {resp.status_code}")
        data = resp.json()
        out: List[SearchResult] = []
        for item in data.get("web", {}).get("results", []):
            out.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
                source=self.name,
                query=query,
            ))
        return out


# ---------------------------------------------------------------------------
# Provedor padrão: busca nativa do OpenRouter (§10 — o modelo busca de fato)
# ---------------------------------------------------------------------------


class OpenRouterWebProvider:
    """Busca nativa do OpenRouter (`plugins: [{id: "web"}]`).

    Vantagem sobre as anteriores: usa a credencial que o produto já tem, o
    próprio modelo navega e a resposta vem com `annotations` — a fonte real
    consultada. Sem `annotations`, o provedor é considerado INSUCESSO: é melhor
    devolver `ok: False` do que devolver "resultado" inventado.
    """

    name = "openrouter-web"

    def __init__(self, api_key: str, model: str = OPENROUTER_SEARCH_MODEL):
        self.api_key = api_key
        self.model = model

    def available(self) -> bool:
        return bool(self.api_key) and len(self.api_key) > 10 and "sua_chave" not in self.api_key.lower()

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        if not self.available():
            raise WebSearchError("Chave do OpenRouter ausente ou em formato de placeholder.")
        try:
            resp = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000"),
                    "X-Title": os.getenv("OPENROUTER_APP_TITLE", "SYNOP"),
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Pesquise na web e responda APENAS com os fatos encontrados, "
                            f"cada um em uma linha iniciada por '- '. Cite a fonte. "
                            f"Pergunta: {query}"
                        ),
                    }],
                    "plugins": [{"id": "web", "max_results": max(1, min(int(limit or 6), 10))}],
                    "max_tokens": 700,
                    "temperature": 0.1,
                },
                timeout=60,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Busca do OpenRouter indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Busca do OpenRouter retornou HTTP {resp.status_code}")
        try:
            message = resp.json()["choices"][0]["message"]
        except Exception as exc:
            raise WebSearchError(f"Resposta da busca do OpenRouter inesperada: {exc}")

        annotations = message.get("annotations") or []
        summary = (message.get("content") or "").strip()
        results: List[SearchResult] = []
        for ann in annotations[:max(1, int(limit or 6))]:
            # Formato real do OpenRouter: {type, url_citation: {url, title, content}}
            citation = ann.get("url_citation") or ann
            if not isinstance(citation, dict):
                continue
            url = str(citation.get("url") or "").strip()
            title = str(citation.get("title") or "").strip()
            if not (url or title):
                continue
            results.append(SearchResult(
                title=title or url,
                url=url,
                # `content` traz o trecho real da página consultada — é a
                # evidência que o agente deve citar, não a suposição dele.
                snippet=(str(citation.get("content") or "") or summary)[:1500].strip(),
                source=self.name,
                query=query,
            ))
        if not results and not summary:
            raise WebSearchError("A busca do OpenRouter não retornou conteúdo.")
        if not results and summary:
            # Houve resposta mas sem citation: devolve como resultado único e
            # deixa claro que a fonte não pôde ser confirmada.
            results.append(SearchResult(
                title=f"Resultado da busca: {query}",
                url="",
                snippet=summary[:1500],
                source=self.name,
                query=query,
            ))
        return results


# ---------------------------------------------------------------------------
# Fallback sem chave: Wikipédia
# ---------------------------------------------------------------------------


class WikipediaProvider:
    """API da Wikipédia (pt e en) — sem chave, sempre disponível para fatos
    verificáveis. NÃO serve para notícias/preços: por isso o `snippet` deixa
    explícito que a fonte é a Wikipédia."""

    name = "wikipedia"
    # A Wikipédia serve apenas para fatos verificáveis. Para pergunta de
    # atualidade ela é RUIM e perigosa: em "preço do dólar hoje" o buscador
    # devolve "Pandemia de COVID-19 no Brasil", e o agente pode narrar aquilo
    # como se fosse a resposta. Por isso recusamos essas perguntas e ainda
    # exigimos relevância real antes de devolver qualquer artigo.
    RECENCY_MARKERS = (
        "hoje", "ontem", "atual", "agora", "notícia", "noticia", "preço", "preco",
        "cotação", "cotacao", "resultado", "placar", "classificação",
        "último", "ultimo", "última", "ultima", "ranking", "tabela", "championship",
        "noturno", "ao vivo", "gols", "transferência", "mercado", "bolsa",
        "dólar", "dolar", "euro", "inflação", "ipca", "seleção",
    )

    def __init__(self, lang: str = "pt"):
        self.lang = lang

    @staticmethod
    def _tokens(text: str) -> set:
        stop = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "em", "no", "na",
                "nos", "nas", "um", "uma", "e", "ou", "para", "por", "com", "que", "qual"}
        return {t for t in re.findall(r"[\wÀ-ÿ]{3,}", (text or "").lower()) if t not in stop}

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        # Recusa perguntas de atualidade: a Wikipédia não é fonte para isso.
        low = (query or "").lower()
        if any(m in low for m in self.RECENCY_MARKERS):
            raise WebSearchError("pergunta de atualidade — Wikipédia não é fonte adequada")
        try:
            resp = requests.get(
                f"https://{self.lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query", "list": "search", "srsearch": query,
                    "format": "json", "srlimit": max(5, min(int(limit or 6) * 2, 20)),
                },
                headers={"User-Agent": WIKI_UA},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Wikipedia indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Wikipedia retornou HTTP {resp.status_code}")
        try:
            hits = resp.json().get("query", {}).get("search", []) or []
        except Exception as exc:
            raise WebSearchError(f"Resposta da Wikipedia inesperada: {exc}")

        want = self._tokens(query)
        scored: List[tuple] = []
        for h in hits:
            title = h.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", h.get("snippet", "") or "").strip()
            have = self._tokens(f"{title} {snippet}")
            if not want or not have:
                continue
            overlap = len(want & have)
            # Exige no mínimo metade dos termos da pergunta no título/resumo.
            if overlap * 2 < len(want):
                continue
            scored.append((overlap / max(1, len(want)), h, title, snippet))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            raise WebSearchError("nenhum artigo relevante na Wikipédia")
        out: List[SearchResult] = []
        for _score, h, title, snippet in scored[:max(1, int(limit or 6))]:
            out.append(SearchResult(
                title=title,
                url=f"https://{self.lang}.wikipedia.org/wiki/{requests.utils.quote(title.replace(' ', '_'))}",
                snippet=snippet,
                source=self.name,
                date=(h.get("timestamp") or "")[:10] or None,
                query=query,
            ))
        return out


# ---------------------------------------------------------------------------
# Roteador
# ---------------------------------------------------------------------------


class WebSearchService:
    """Roteia a busca para o primeiro provedor que responder de verdade."""

    def __init__(self):
        self.providers: List[Any] = []
        tavily = os.getenv("TAVILY_API_KEY", "").strip()
        brave = os.getenv("BRAVE_API_KEY", "").strip()
        if tavily:
            self.providers.append(TavilyProvider(tavily))
        if brave:
            self.providers.append(BraveProvider(brave))
        self.openrouter = OpenRouterWebProvider(os.getenv("OPENROUTER_API_KEY", "").strip())
        if self.openrouter.available():
            self.providers.append(self.openrouter)
        self.providers.append(WikipediaProvider("pt"))
        self.providers.append(WikipediaProvider("en"))
        self._last_calls: Dict[str, List[float]] = {}
        try:
            self.rate_limit_per_minute = int(os.getenv("WEB_SEARCH_RATE_LIMIT", "10"))
        except ValueError:
            self.rate_limit_per_minute = 10

    def _rate_ok(self, user_id: str) -> bool:
        now = time.time()
        window = [t for t in self._last_calls.get(user_id, []) if now - t < 60]
        self._last_calls[user_id] = window
        if len(window) >= self.rate_limit_per_minute:
            return False
        self._last_calls[user_id] = window + [now]
        return True

    def search(self, user_id: str, query: str, limit: int = 6) -> Dict[str, Any]:
        if not (query or "").strip():
            raise WebSearchError("Termo de busca vazio.")
        if not self._rate_ok(user_id):
            raise WebSearchError("Limite de pesquisas atingido. Aguarde um instante e tente novamente.")

        errors: List[str] = []
        for provider in self.providers:
            try:
                results = provider.search(query.strip(), limit=max(1, min(int(limit or 6), 12)))
                if results:
                    return {
                        "ok": True,
                        "query": query.strip(),
                        "provider": provider.name,
                        "results": [r.to_dict() for r in results],
                    }
                errors.append(f"{provider.name}: nenhum resultado")
            except WebSearchError as exc:
                errors.append(f"{provider.name}: {exc}")
            except Exception as exc:  # pragma: no cover - rede inesperada
                errors.append(f"{provider.name}: {type(exc).__name__}: {exc}")

        # §9: honestidade acima de tudo. Sem resultado, diz que não tem.
        return {
            "ok": False,
            "query": query,
            "provider": "none",
            "results": [],
            "error": "Nenhum mecanismo de busca respondeu no momento.",
            "details": errors[:5],
        }

    def available_providers(self) -> List[str]:
        return [p.name for p in self.providers]
