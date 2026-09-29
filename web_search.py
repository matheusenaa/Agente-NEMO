"""
NEMO — Web Search Service (missão §9, §10, §36).

Camada que esconde as diferenças entre mecanismos de busca. Nenhum resultado é
inventado: se todos os provedores falharem, o serviço devolve `ok: False` com o
motivo real de cada tentativa, e o agente é obrigado a avisar o usuário.

Ordem dos provedores (primeiro que responder vence):
  1. Tavily   — TAVILY_API_KEY   (melhor qualidade, JSON)
  2. Brave    — BRAVE_API_KEY    (JSON)
  3. Bing     — sem chave        (HTML; funciona em redes que bloqueiam o DuckDuckGo)
  4. DuckDuckGo — sem chave      (HTML; pode responder 202 = desafio anti-bot)
  5. Wikipedia — sem chave       (API JSON; rede de segurança para perguntas factuais)

A pesquisa NUNCA é automática para toda pergunta — o agente decide quando precisa
de informação externa (ver `_needs_search` em nemo_server.py).
"""

from __future__ import annotations

import base64
import binascii
import html as html_lib
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import requests

load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


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


def _strip_tags(fragment: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment or ""))


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", _strip_tags(fragment)).strip()


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


class BingProvider:
    """Bing sem chave. O Bing embrulha os links em redirecionadores
    `bing.com/ck/a?...&u=a1<base64url>`; `_unwrap` devolve a URL real."""

    name = "bing"

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://www.bing.com/search",
                params={"q": query, "setlang": "pt-br", "cc": "BR", "count": max(10, limit)},
                headers=BROWSER_HEADERS,
                timeout=20,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Bing indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Bing retornou HTTP {resp.status_code}")
        return self._parse(resp.text, query, limit)

    @staticmethod
    def _unwrap(url: str) -> str:
        if "bing.com/ck/a" not in url:
            return url
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(html_lib.unescape(url)).query)
        raw = (qs.get("u") or [""])[0]
        if not raw.startswith("a1"):
            return url
        payload = raw[2:]
        payload += "=" * (-len(payload) % 4)
        try:
            return base64.urlsafe_b64decode(payload).decode("utf-8", "replace")
        except (binascii.Error, ValueError):
            return url

    def _parse(self, page: str, query: str, limit: int) -> List[SearchResult]:
        results: List[SearchResult] = []
        for block in re.split(r'<li class="b_algo"', page)[1:]:
            if len(results) >= limit:
                break
            head = re.search(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
            if not head:
                continue
            url = self._unwrap(head.group(1))
            title = _clean(head.group(2))
            snippet = ""
            cap = re.search(r'<div class="b_caption">(.*?)</div>', block, re.DOTALL)
            if cap:
                snippet = _clean(cap.group(1))[:400]
            if not title or not url.startswith("http"):
                continue
            results.append(SearchResult(title=title, url=url, snippet=snippet, source=self.name, query=query))
        return results


class DuckDuckGoProvider:
    """DuckDuckGo HTML (sem chave). Pode responder HTTP 202 com um desafio
    anti-bot — nesse caso o status é tratado como falha explícita, para o
    serviço cair no próximo provedor em vez de devolver lista vazia."""

    name = "duckduckgo"

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=BROWSER_HEADERS,
                timeout=15,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"DuckDuckGo indisponível: {exc}")
        if resp.status_code == 202:
            raise WebSearchError("DuckDuckGo exigiu desafio anti-bot (HTTP 202).")
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
                snippet = _clean(s.group(1))[:400]
            if url and title:
                results.append(SearchResult(
                    title=title, url=url, snippet=snippet or "", source=self.name, query=query,
                ))
        return results


class WikipediaProvider:
    """API da Wikipédia (sem chave). Rede de segurança: sempre responde JSON e
    cobre bem perguntas factuais como 'qual a capital do Brasil'."""

    name = "wikipedia"

    def search(self, query: str, limit: int = 6) -> List[SearchResult]:
        try:
            resp = requests.get(
                "https://pt.wikipedia.org/w/api.php",
                params={
                    "action": "query", "list": "search", "srsearch": query,
                    "srlimit": max(1, min(int(limit), 10)), "format": "json", "utf8": 1,
                },
                headers={"User-Agent": f"NEMO-SYNOP/1.0 ({USER_AGENT})"},
                timeout=15,
            )
        except requests.RequestException as exc:
            raise WebSearchError(f"Wikipedia indisponível: {exc}")
        if resp.status_code != 200:
            raise WebSearchError(f"Wikipedia retornou HTTP {resp.status_code}")
        data = resp.json()
        out: List[SearchResult] = []
        for item in (data.get("query", {}) or {}).get("search", []) or []:
            title = _clean(item.get("title", ""))
            if not title:
                continue
            url = "https://pt.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            out.append(SearchResult(
                title=title,
                url=url,
                snippet=_clean(item.get("snippet", ""))[:400],
                source=self.name,
                query=query,
                date=_iso_or_none(item.get("timestamp")),
            ))
        return out


def _iso_or_none(ts: Optional[str]) -> Optional[str]:
    if not ts:
        return None
    return str(ts).replace("Z", "").replace("T", " ")[:19]


class WebSearchService:
    """Roteia a busca para o primeiro provedor configurado que responder."""

    def __init__(self):
        self.providers: List[Any] = []
        self.provider_errors: Dict[str, str] = {}
        tavily = os.getenv("TAVILY_API_KEY", "").strip()
        brave = os.getenv("BRAVE_API_KEY", "").strip()
        if tavily:
            self.providers.append(TavilyProvider(tavily))
        if brave:
            self.providers.append(BraveProvider(brave))
        self.providers.append(BingProvider())
        self.providers.append(DuckDuckGoProvider())
        self.providers.append(WikipediaProvider())
        self._last_calls: Dict[str, List[float]] = {}
        self.rate_limit_per_minute = int(os.getenv("WEB_SEARCH_RATE_LIMIT", "10"))

    def _rate_ok(self, user_id: str) -> bool:
        now = time.time()
        window = [t for t in self._last_calls.get(user_id, []) if now - t < 60]
        if len(window) >= self.rate_limit_per_minute:
            self._last_calls[user_id] = window
            return False
        self._last_calls[user_id] = window + [now]
        return True

    def search(self, user_id: str, query: str, limit: int = 6) -> Dict[str, Any]:
        if not (query or "").strip():
            raise WebSearchError("Termo de busca vazio.")
        if not self._rate_ok(user_id):
            raise WebSearchError("Limite de pesquisas atingido. Aguarde um instante e tente novamente.")
        errors: Dict[str, str] = {}
        for provider in self.providers:
            try:
                results = provider.search(query.strip(), limit=max(1, min(int(limit or 6), 12)))
            except WebSearchError as exc:
                errors[provider.name] = str(exc)
                continue
            except Exception as exc:  # provedor inesperado não pode derrubar a busca
                errors[provider.name] = f"{type(exc).__name__}: {exc}"
                continue
            if results:
                return {
                    "ok": True,
                    "query": query.strip(),
                    "provider": provider.name,
                    "results": [r.to_dict() for r in results],
                }
            errors[provider.name] = "respondeu sem resultados."
        self.provider_errors = errors
        return {
            "ok": False,
            "query": query,
            "provider": "none",
            "results": [],
            "error": "Nenhum mecanismo de busca respondeu no momento.",
            "provider_errors": errors,
        }

    def available_providers(self) -> List[str]:
        return [p.name for p in self.providers]
