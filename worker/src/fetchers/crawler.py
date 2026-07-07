"""dedup/cap 이후 실제 발송 대상 기사만 본문을 보강하는 크롤러.

Naver API/Google RSS의 요약이 부실할 때(특히 Google RSS는 출처/날짜 파편인
경우가 많음) 본문을 크롤링해 LLM 요약의 입력 품질을 높이는 용도다. API가 없는
사이트를 새로 발굴하는 것은 사이트별 유지보수 부담이 커서 범위 밖으로 둔다.

실패(차단/타임아웃/robots 거부/추출 실패)하면 항상 원본 요약(NewsItem.summary)으로
자연스럽게 폴백하도록, 이 모듈은 실패 시 None만 반환하고 예외를 던지지 않는다.
"""

from __future__ import annotations

import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_USER_AGENT = "NewsDigestBot/1.0 (Personal News Digest; +mailto:nakwanyu@gmail.com)"
_TIMEOUT_SECONDS = 8
_MIN_CONTENT_LENGTH = 50
_MAX_CONTENT_LENGTH = 1500
_CRAWL_DELAY_SECONDS = 0.5

_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_last_fetch_at: dict[str, float] = {}


def _allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _robots_cache:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        try:
            parser.read()
        except Exception:
            # robots.txt를 읽을 수 없으면 보수적으로 허용(대부분의 뉴스 사이트는 robots.txt가 없거나 관대함)
            parser = None
        _robots_cache[origin] = parser

    parser = _robots_cache[origin]
    return parser is None or parser.can_fetch(_USER_AGENT, url)


def _throttle(domain: str) -> None:
    last = _last_fetch_at.get(domain)
    if last is not None:
        elapsed = time.monotonic() - last
        if elapsed < _CRAWL_DELAY_SECONDS:
            time.sleep(_CRAWL_DELAY_SECONDS - elapsed)
    _last_fetch_at[domain] = time.monotonic()


def _fetch_html(url: str) -> str | None:
    _throttle(urlparse(url).netloc)
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.info("크롤링 요청 실패 (url=%s): %s", url, e)
        return None


def _extract_meta_description(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for attrs in ({"property": "og:description"}, {"name": "description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def fetch_article_content(url: str) -> str | None:
    """기사 본문을 추출해 최대 _MAX_CONTENT_LENGTH자로 반환한다. 실패 시 None."""
    if not _allowed_by_robots(url):
        logger.info("robots.txt에 의해 크롤링이 차단됨: %s", url)
        return None

    try:
        html_text = _fetch_html(url)
        if not html_text:
            return None

        content = (trafilatura.extract(html_text) or "").strip()
        if len(content) < _MIN_CONTENT_LENGTH:
            content = _extract_meta_description(html_text)

        if len(content) < _MIN_CONTENT_LENGTH:
            return None

        return content[:_MAX_CONTENT_LENGTH]
    except Exception as e:
        logger.info("크롤링/추출 중 예상 못 한 오류 (url=%s): %s", url, e)
        return None


def enrich_with_crawled_content(items, cache_lookup, cache_store) -> None:
    """발송 대상 items에 대해 캐시 조회 -> 미스 시 크롤링 순서로 item.content를 채운다.

    cache_lookup(url) -> Optional[str] (캐시에 없으면 None)
    cache_store(url, content) -> None (크롤링 결과를 저장소에 반영)
    """
    for item in items:
        cached = cache_lookup(item.link)
        if cached is not None:
            item.content = cached or None
            continue
        content = fetch_article_content(item.link)
        item.content = content
        cache_store(item.link, content or "")
