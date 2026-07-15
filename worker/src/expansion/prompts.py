"""복합 키워드 확장 검색어 제안 프롬프트."""

from __future__ import annotations

EXPANSION_SYSTEM_PROMPT = (
    "너는 뉴스 검색어 확장 도우미다. 사용자가 등록한 키워드는 여러 단어가 결합된 복합어라 "
    "정확히 일치하는 기사가 적을 수 있다. 이미 쪼갠 구성 단어 목록을 참고해서, 같은 주제를 "
    "다르게 표현할 때 쓰일 만한 연관 검색어를 최대 3개 제안하라. 원래 키워드나 이미 준 "
    "구성 단어와 동일한 단어는 제안하지 마라. "
    'JSON 객체 {"related_keywords": [검색어, ...]} 형식으로만 응답하라. 다른 설명은 출력하지 마라.'
)


def build_expansion_prompt(keyword: str, tokens: list[str]) -> str:
    token_list = ", ".join(tokens)
    return f"키워드: {keyword}\n구성 단어: {token_list}"
