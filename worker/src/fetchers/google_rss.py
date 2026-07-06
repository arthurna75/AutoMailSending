"""구글 뉴스 RSS 수집기 (API 키 불필요).

https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko

주의(알려진 제한): RSS의 summary는 실제 한 줄 요약이 아니라 출처/날짜 조각인 경우가 많다.
기사 본문 페이지를 추가로 크롤링해 진짜 요약을 만드는 것은 이 프로그램의 범위 밖이다.
"""

from __future__ import annotations

import logging
import urllib.parse

import feedparser

from src.fetchers.base import NewsItem
from src.utils.htmlclean import strip_html

logger = logging.getLogger(__name__)

_RSS_BASE = "https://news.google.com/rss/search"
_TIMEOUT_SECONDS = 10


class GoogleNewsRssFetcher:
    def __init__(self, hl: str = "ko", gl: str = "KR", ceid: str = "KR:ko"):
        self._hl = hl
        self._gl = gl
        self._ceid = ceid

    def fetch(self, keyword: str, count: int) -> list[NewsItem]:
        query = urllib.parse.quote(keyword)
        url = f"{_RSS_BASE}?q={query}&hl={self._hl}&gl={self._gl}&ceid={self._ceid}"

        try:
            feed = feedparser.parse(url)
        except Exception:
            logger.exception("구글 뉴스 RSS 파싱 실패 (keyword=%s)", keyword)
            return []

        if getattr(feed, "bozo", False) and not feed.entries:
            logger.warning("구글 뉴스 RSS 응답이 비어있거나 형식 오류 (keyword=%s)", keyword)
            return []

        items: list[NewsItem] = []
        for entry in feed.entries[:count]:
            link = entry.get("link", "")
            if not link:
                continue
            summary_raw = entry.get("summary", entry.get("description", ""))
            items.append(
                NewsItem(
                    title=strip_html(entry.get("title", "")),
                    link=link,
                    summary=strip_html(summary_raw),
                    source="google",
                    keyword=keyword,
                    published=entry.get("published"),
                )
            )
        return items
