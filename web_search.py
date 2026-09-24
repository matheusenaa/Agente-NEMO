"""
NEMO — Web Search Service (missão §20-21, §49).

Camada que esconde as diferenças entre mecanismos de busca. Hoje usa o
DuckDuckGo (sem chave) como padrão e aceita Tavily / Brave quando configurados.
A pesquisa NUNCA é automática para toda pergunta — o agente decide quando
precisa de informação externa (ver _needs_search em nemo_server.py).
"""

from __future__ import annotations

import html as html_lib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 NEMO/1.0"


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
    pass


class DuckDuckGoProvider:
    """DuckDuckGo HTML (sem chave). Suficiente para a Rebeca Referência."""

    name = "duckduckgo"

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"DuckDuckGo indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"DuckDuckGo retornou HTTP {resp.status_code}")
        return self._parse(resp.text, query, limit)

    def _parse(self, page: str, query: str, limit: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        # cada resultado vem em <a class="result__a" href="...">titulo</a> e <a class="result__snippet">
        blocks = re.split(r'<a class="result__a"', page)[1:]
        for block in blocks:
            if len(results) >= limit:
                break
            title = ""
            url = ""
            t = re.search(r'href="([^"]+)"[^>]*>([^<]*)<', block)
            if t:
                url = html_lib.unescape(t.group(1))
                title = html_lib.unescape(t.group(2)).strip()
            snippet = ""
            s = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
            if s:
                snippet = html_lib.unescape(re.sub(r"<[^>]+>", "", s.group(1))).strip()
            if url and title:
                results.append(SearchResult(
                    title=title, url=url, snippet=snippet or "", source=self.name, query=query,
                ))
        return results


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


class WebSearchService:
    """Roteia a busca para o primeiro provedor configurado (DDG é o padrão sem key)."""

    def __init__(self):
        self.providers: List[Any] = []
        tavily = os.getenv("TAVILY_API_KEY", "").strip()
        brave = os.getenv("BRAVE_API_KEY", "").strip()
        if tavily:
            self.providers.append(TavilyProvider(tavily))
        if brave:
            self.providers.append(BraveProvider(brave))
        self.providers.append(DuckDuckGoProvider())  # sempre no final como fallback
        self._last_calls: Dict[str, List[float]] = {}
        self.rate_limit_per_minute = int(os.getenv("WEB_SEARCH_RATE_LIMIT", "10"))

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
            except WebSearchError:
                continue
            except Exception:
                continue
        return {"ok": False, "query": query, "provider": "none", "results": [],
                "error": "Nenhum mecanismo de busca respondeu no momento."}

    def available_providers(self) -> List[str]:
        return [p.name for p in self.providers]