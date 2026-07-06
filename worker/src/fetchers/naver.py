"""네이버 검색 API(뉴스) 수집기.

https://openapi.naver.com/v1/search/news.json
- 인증: X-Naver-Client-Id / X-Naver-Client-Secret 헤더 (developers.naver.com 무료 발급)
- display: 결과 개수 (최대 100)
- sort: date(최신순) 또는 sim(정확도순)
"""

from __future__ import annotations

import logging

import requests

from src.fetchers.base import NewsItem
from src.utils.htmlclean import clean_naver_text

logger = logging.getLogger(__name__)

_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
_TIMEOUT_SECONDS = 10


def _request(client_id: str, client_secret: str, params: dict) -> requests.Response:
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    return requests.get(_ENDPOINT, headers=headers, params=params, timeout=_TIMEOUT_SECONDS)


def check_credentials(client_id: str, client_secret: str) -> tuple[bool, str]:
    """네이버 API 자격증명이 유효한지 가벼운 호출로 확인한다. (성공여부, 오류메시지)"""
    try:
        response = _request(client_id, client_secret, {"query": "테스트", "display": 1, "start": 1})
    except requests.RequestException as e:
        return False, f"네이버 API에 연결할 수 없습니다: {e}"

    if response.status_code == 200:
        return True, ""
    if response.status_code in (401, 403):
        return False, "클라이언트 ID/Secret이 올바르지 않습니다."
    return False, f"네이버 API 오류 (status={response.status_code}): {response.text[:200]}"


class NaverNewsFetcher:
    def __init__(self, client_id: str, client_secret: str, sort: str = "date"):
        self._client_id = client_id
        self._client_secret = client_secret
        self._sort = sort

    def fetch(self, keyword: str, count: int) -> list[NewsItem]:
        display = max(1, min(count, 100))
        params = {
            "query": keyword,
            "display": display,
            "start": 1,
            "sort": self._sort,
        }

        try:
            response = _request(self._client_id, self._client_secret, params)
        except requests.RequestException:
            logger.exception("네이버 뉴스 API 호출 실패 (keyword=%s)", keyword)
            return []

        if response.status_code != 200:
            logger.warning(
                "네이버 뉴스 API 오류 응답 (keyword=%s, status=%s): %s",
                keyword, response.status_code, response.text[:200],
            )
            return []

        payload = response.json()
        items: list[NewsItem] = []
        for raw_item in payload.get("items", []):
            link = raw_item.get("originallink") or raw_item.get("link") or ""
            if not link:
                continue
            items.append(
                NewsItem(
                    title=clean_naver_text(raw_item.get("title", "")),
                    link=link,
                    summary=clean_naver_text(raw_item.get("description", "")),
                    source="naver",
                    keyword=keyword,
                    published=raw_item.get("pubDate"),
                )
            )
        return items
