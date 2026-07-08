"""키워드 관련성 판단 프롬프트. 제목만 보고 사용자 의도에 맞는 기사 번호를 JSON으로 받는다."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "너는 뉴스 키워드 필터링 도우미다. 사용자가 등록한 키워드는 동음이의어를 가질 수 있고, "
    "사용자는 자신이 원하는 의미를 '사용자 의도' 설명으로 알려준다. 번호가 매겨진 기사 제목 "
    "목록을 보고, 그 의도에 부합하는 기사의 번호만 골라라. 애매하면 포함시켜라(관련 없는 것이 "
    "명백한 경우에만 제외). "
    'JSON 객체 {"relevant_indices": [번호, ...]} 형식으로만 응답하라. 다른 설명은 출력하지 마라.'
)


def build_user_prompt(keyword: str, hint: str, titles: list[str]) -> str:
    numbered = "\n".join(f"{i}. {title}" for i, title in enumerate(titles, start=1))
    return f"키워드: {keyword}\n사용자 의도: {hint}\n기사 제목 목록:\n{numbered}"
