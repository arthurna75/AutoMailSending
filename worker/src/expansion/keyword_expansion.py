"""복합 키워드 확장 검색 — 여러 단어로 이뤄진 키워드의 검색 결과가 부족할 때, 구성
단어 및 연관 검색어로 재검색해 후보 풀을 넓힌다."""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from src.expansion.prompts import EXPANSION_SYSTEM_PROMPT, build_expansion_prompt
from src.filtering.relevance_filter import FilterUsage

logger = logging.getLogger(__name__)

_STOPWORD_TOKENS = {"관련", "소식", "뉴스", "및", "기사"}


def split_keyword_tokens(keyword: str) -> list[str]:
    """공백으로 구분된 복합 키워드를 구성 단어로 쪼갠다.

    단일어 키워드는 쪼갤 대상이 없으므로 빈 리스트를 반환해 확장 대상에서 자연히 제외된다.
    """
    raw_tokens = keyword.split()
    if len(raw_tokens) < 2:
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        if len(token) < 2 or token in _STOPWORD_TOKENS or token == keyword:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def related_keywords_via_llm(keyword: str, tokens: list[str], model: str) -> tuple[list[str], FilterUsage]:
    """구성 단어 분해로도 후보가 부족할 때만 호출하는 선택적 1회 LLM 확장.

    API 오류/응답 파싱 실패 시 fail-open(빈 리스트 반환) — 확장을 못 받는 것뿐이지
    기존에 이미 확보한 기사가 사라지지는 않는다.
    """
    usage = FilterUsage()
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXPANSION_SYSTEM_PROMPT},
                {"role": "user", "content": build_expansion_prompt(keyword, tokens)},
            ],
        )
        usage.llm_calls += 1
        usage.prompt_tokens += response.usage.prompt_tokens
        usage.completion_tokens += response.usage.completion_tokens

        payload = json.loads(response.choices[0].message.content or "{}")
        related = payload.get("related_keywords")
        if not isinstance(related, list):
            raise ValueError(f"related_keywords가 리스트가 아닙니다: {payload!r}")

        existing = {keyword, *tokens}
        cleaned = [str(term).strip() for term in related if str(term).strip()]
        deduped = [term for term in dict.fromkeys(cleaned) if term not in existing]
        return deduped[:3], usage
    except Exception:
        logger.exception("연관 키워드 확장 실패, 건너뜁니다 (keyword=%s)", keyword)
        return [], usage
