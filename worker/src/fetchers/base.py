"""뉴스 수집기 공통 타입."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    keyword: str
    published: Optional[str] = None
    content: Optional[str] = None       # 크롤링으로 보강한 본문(있으면)
    llm_summary: Optional[str] = None   # LLM 요약(있으면 이메일에서 summary 대신 사용)


class NewsFetcher(Protocol):
    def fetch(self, keyword: str, count: int) -> list[NewsItem]:
        ...
