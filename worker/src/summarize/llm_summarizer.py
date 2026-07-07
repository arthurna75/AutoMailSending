"""LLM 기사 요약 — 신뢰성과 단순함을 우선한다(토큰 비용은 고려하지 않음).

기사마다 개별적으로 OpenAI를 호출한다: 한 기사의 요약이 실패해도 다른 기사에 영향을 주지
않는다(배치 처리 시 발생하는 "응답 파싱 실패 -> 배치 전체가 스니펫으로 강등" 위험 회피).
URL 기준 전역 캐시(article_cache)만 유지한다 — 여러 사용자가 같은 기사를 구독해도 중복
크롤링/요약을 피하고, 크롤링 본문을 영속 저장하는 역할도 겸하기 때문에 순수 비용 최적화가
아니라 실질적으로 필요한 구조다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import OpenAI

from src.summarize.cache import fetch_cached_rows, upsert_cache_row, url_hash
from src.summarize.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_EXCERPT_MAX_CHARS = 1200
_MAX_OUTPUT_TOKENS = 120


@dataclass
class SummaryUsage:
    llm_calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _cache_row(item, hash_value: str, summary: str, model: str, usage=None) -> dict:
    return {
        "url_hash": hash_value,
        "url": item.link,
        "title": item.title,
        "raw_summary": item.summary,
        "crawled_content": item.content,
        "llm_summary": summary,
        "llm_model": model,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }


def summarize_items(items, supabase, model: str) -> SummaryUsage:
    """items(발송 대상 NewsItem 목록)의 item.llm_summary를 채운다.

    캐시 미스 기사마다 OpenAI를 1회씩 호출하고, 실패한 기사는 원본 스니펫으로 폴백한다.
    """
    usage = SummaryUsage()
    hashes = {url_hash(item.link): item for item in items}
    cached = fetch_cached_rows(supabase, list(hashes))

    client = OpenAI()
    for hash_value, item in hashes.items():
        row = cached.get(hash_value)
        if row and row.get("llm_summary"):
            item.llm_summary = row["llm_summary"]
            usage.cache_hits += 1
            continue

        content = (row.get("crawled_content") if row else None) or item.content or item.summary
        excerpt = (content or "")[:_EXCERPT_MAX_CHARS]

        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=_MAX_OUTPUT_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(item.title, excerpt)},
                ],
            )
            summary = (response.choices[0].message.content or "").strip() or item.summary
            usage.llm_calls += 1
            usage.prompt_tokens += response.usage.prompt_tokens
            usage.completion_tokens += response.usage.completion_tokens
            upsert_cache_row(supabase, _cache_row(item, hash_value, summary, model, response.usage))
        except Exception:
            logger.exception("LLM 요약 실패, 원본 스니펫으로 대체합니다 (url=%s)", item.link)
            summary = item.summary

        item.llm_summary = summary

    return usage
