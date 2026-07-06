"""LLM 요약 프롬프트. 배치 내 모든 기사가 system 프롬프트 1개를 공유해
고정 오버헤드를 배치 크기로 나눠 절감한다."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "너는 한국어 뉴스 요약가다. 입력된 각 기사를 1~2문장, 80자 이내로 핵심만 요약하라. "
    "다른 설명 없이 반드시 아래 JSON 형식으로만 응답하라:\n"
    '{"summaries": [{"id": "<id>", "summary": "<요약>"}, ...]}'
)


def build_user_prompt(batch: list[dict]) -> str:
    lines = []
    for entry in batch:
        excerpt = entry["excerpt"].replace("\n", " ").strip()
        lines.append(f'- id: {entry["id"]}\n  title: {entry["title"]}\n  excerpt: {excerpt}')
    return "다음 기사들을 요약하라:\n\n" + "\n\n".join(lines)
