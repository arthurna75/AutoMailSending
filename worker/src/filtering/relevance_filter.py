"""키워드 의도 힌트 기반 관련성 필터 — 힌트가 있는 키워드만 LLM 제목 분류로 걸러낸다."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from src.aggregation.aggregator import group_by_keyword
from src.fetchers.base import NewsItem
from src.filtering.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


@dataclass
class FilterUsage:
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


def filter_by_relevance(
    items: list[NewsItem], keyword_hints: dict[str, str], model: str
) -> tuple[list[NewsItem], FilterUsage]:
    """힌트가 등록된 키워드의 아이템만 LLM으로 관련성을 판단해 걸러낸다.

    힌트가 없는 키워드의 아이템은 그대로 통과한다(LLM 호출 없음, 비용 미증가).
    API 오류/응답 파싱 실패 시 해당 키워드 아이템은 전부 유지한다(fail-open) — 무관한
    기사를 놓치는 것보다 관련 기사를 실수로 빠뜨리지 않는 쪽을 택한다.
    """
    usage = FilterUsage()
    groups = group_by_keyword(items)

    client: OpenAI | None = None
    result: list[NewsItem] = []

    for keyword, group in groups.items():
        hint = (keyword_hints.get(keyword) or "").strip()
        if not hint:
            result.extend(group)
            continue

        if client is None:
            client = OpenAI()

        titles = [item.title for item in group]
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(keyword, hint, titles)},
                ],
            )
            usage.llm_calls += 1
            usage.prompt_tokens += response.usage.prompt_tokens
            usage.completion_tokens += response.usage.completion_tokens

            payload = json.loads(response.choices[0].message.content or "{}")
            indices = payload.get("relevant_indices")
            if not isinstance(indices, list):
                raise ValueError(f"relevant_indices가 리스트가 아닙니다: {payload!r}")

            kept_positions = {int(i) - 1 for i in indices}
            result.extend(item for pos, item in enumerate(group) if pos in kept_positions)
        except Exception:
            logger.exception(
                "관련성 필터 실패, 해당 키워드 기사를 모두 유지합니다 (keyword=%s)", keyword
            )
            result.extend(group)

    return result, usage
