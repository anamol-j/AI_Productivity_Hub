from __future__ import annotations

from dataclasses import dataclass

from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    title: str
    href: str
    body: str


def search_web(topic: str, max_results: int = 5) -> list[SearchResult]:
    with DDGS() as ddgs:
        results = ddgs.text(topic, max_results=max_results)
        return [
            SearchResult(
                title=item.get("title", "Untitled"),
                href=item.get("href", ""),
                body=item.get("body", ""),
            )
            for item in results
        ]


def format_sources(results: list[SearchResult]) -> str:
    formatted: list[str] = []
    for idx, result in enumerate(results, start=1):
        formatted.append(
            f"Source {idx}\nTitle: {result.title}\nURL: {result.href}\nSummary: {result.body}"
        )
    return "\n\n".join(formatted)
