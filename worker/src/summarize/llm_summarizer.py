"""LLM 기사 요약 — 토큰/비용 절약이 핵심 설계 목표.

절약 전략:
1. dedup/cap 이후 실제 발송될 기사에만 적용한다(수집 전체가 아니라 ~20건 한정).
2. 전역 캐시(article_cache)를 URL 기준으로 우선 조회한다 — 여러 사용자가 같은
   기사를 구독해도 LLM 호출은 1회뿐이다.
3. 스니펫이 이미 완결된 문장형이면 LLM을 생략하고 원본을 그대로 쓴다.
4. 캐시 미스 건들을 배치로 묶어 한 번의 API 호출로 처리한다(고정 프롬프트
   오버헤드를 배치 크기만큼 나눠 절감).
5. 입력 본문은 지정 길이로 truncate하고, 출력은 프롬프트 지시 + max_tokens로
   이중 제한한다.
6. 일일 비용 상한(remaining_budget_usd)을 초과하면 남은 건은 전부 원본 스니펫으로
   대체해 비용 폭주를 막는다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from src.summarize.cache import fetch_cached_rows, upsert_cache_row, url_hash
from src.summarize.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_BATCH_SIZE = 8
_EXCERPT_MAX_CHARS = 1200
_SNIPPET_SKIP_MAX_LEN = 120
_MAX_TOKENS_PER_ARTICLE = 80

# gpt-4o-mini 기준 대략적인 단가(USD/1K tokens). 실제 요금은 OpenAI 가격표 변경 시 갱신 필요.
_PRICE_PER_1K_PROMPT = 0.00015
_PRICE_PER_1K_COMPLETION = 0.0006


@dataclass
class SummaryUsage:
    llm_calls: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.prompt_tokens / 1000 * _PRICE_PER_1K_PROMPT
            + self.completion_tokens / 1000 * _PRICE_PER_1K_COMPLETION
        )


def _looks_like_full_sentence(text: str) -> bool:
    return bool(text) and text.rstrip().endswith((".", "다", "요", "다.", "요.", "!", "?"))


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


def _parse_response(raw: str) -> dict[str, str]:
    try:
        data = json.loads(raw)
        return {entry["id"]: entry["summary"] for entry in data.get("summaries", [])}
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("LLM 응답 파싱 실패, 원본 스니펫을 사용합니다: %s", raw[:200])
        return {}


def summarize_items(items, supabase, model: str, remaining_budget_usd: float) -> SummaryUsage:
    """items(발송 대상 NewsItem 목록)의 item.llm_summary를 채운다.

    예산 초과 시 남은 항목은 원본 스니펫을 그대로 llm_summary에 채워 폴백한다.
    """
    usage = SummaryUsage()
    hashes = {url_hash(item.link): item for item in items}
    cached = fetch_cached_rows(supabase, list(hashes))

    need_llm: list[tuple[str, object, str]] = []
    for hash_value, item in hashes.items():
        row = cached.get(hash_value)
        if row and row.get("llm_summary"):
            item.llm_summary = row["llm_summary"]
            usage.cache_hits += 1
            continue

        if _looks_like_full_sentence(item.summary) and len(item.summary) <= _SNIPPET_SKIP_MAX_LEN:
            item.llm_summary = item.summary
            upsert_cache_row(supabase, _cache_row(item, hash_value, item.summary, "skipped-snippet"))
            continue

        content = (row.get("crawled_content") if row else None) or item.content or item.summary
        need_llm.append((hash_value, item, (content or "")[:_EXCERPT_MAX_CHARS]))

    if not need_llm:
        return usage

    client = OpenAI()
    for batch_start in range(0, len(need_llm), _BATCH_SIZE):
        if usage.estimated_cost_usd >= remaining_budget_usd:
            skipped = need_llm[batch_start:]
            logger.warning("일일 LLM 비용 상한 도달, 남은 %d건은 원본 스니펫으로 대체합니다.", len(skipped))
            for _, item, _excerpt in skipped:
                item.llm_summary = item.summary
            break

        batch = need_llm[batch_start : batch_start + _BATCH_SIZE]
        payload = [
            {"id": hash_value, "title": item.title, "excerpt": excerpt}
            for hash_value, item, excerpt in batch
        ]

        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=_MAX_TOKENS_PER_ARTICLE * len(batch),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(payload)},
            ],
        )
        usage.llm_calls += 1
        usage.prompt_tokens += response.usage.prompt_tokens
        usage.completion_tokens += response.usage.completion_tokens

        summaries_by_id = _parse_response(response.choices[0].message.content)
        for hash_value, item, _excerpt in batch:
            summary = summaries_by_id.get(hash_value, item.summary)
            item.llm_summary = summary
            upsert_cache_row(supabase, _cache_row(item, hash_value, summary, model, response.usage))

    return usage
