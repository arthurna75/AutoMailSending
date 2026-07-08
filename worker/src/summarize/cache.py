"""전역 기사 요약 캐시(article_cache) 조회/저장.

여러 사용자가 같은 키워드를 구독해 같은 기사를 여러 번 수집하더라도, URL 기준으로
크롤링·LLM 요약을 1회만 수행하고 재사용하는 것이 토큰/비용 절약의 핵심이다.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), parts.query, ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def fetch_cached_rows(supabase, url_hashes: list[str]) -> dict[str, dict]:
    if not url_hashes:
        return {}
    resp = supabase.table("article_cache").select("*").in_("url_hash", url_hashes).execute()
    return {row["url_hash"]: row for row in resp.data}


def upsert_cache_row(supabase, row: dict) -> None:
    supabase.table("article_cache").upsert(row, on_conflict="url_hash").execute()
