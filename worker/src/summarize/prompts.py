"""LLM 요약 프롬프트. 기사 1건당 1회 호출하므로 응답은 요약문 텍스트만 받는다(JSON 불필요)."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "너는 한국어 뉴스 요약가다. 입력된 기사를 1~2문장, 80자 이내로 핵심만 요약하라. "
    "다른 설명 없이 요약문만 출력하라."
)


def build_user_prompt(title: str, excerpt: str) -> str:
    cleaned = excerpt.replace("\n", " ").strip()
    return f"title: {title}\nexcerpt: {cleaned}"
