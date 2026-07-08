"""LLM 요약 프롬프트. 기사 1건당 1회 호출하므로 응답은 요약문 텍스트만 받는다(JSON 불필요)."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "너는 한국어 뉴스 요약가다. 입력된 기사의 핵심 내용을 2~3문장, 한글 기준 80자 이상 "
    "120자 이내 분량으로 구체적으로 요약하라. 80자보다 짧게 요약하지 말고 120자를 넘기지 "
    "마라. 다른 설명 없이 요약문만 출력하라."
)


def build_user_prompt(title: str, excerpt: str) -> str:
    cleaned = excerpt.replace("\n", " ").strip()
    return f"title: {title}\nexcerpt: {cleaned}"
