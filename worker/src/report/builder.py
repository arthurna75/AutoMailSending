"""HTML 다이제스트 생성 (로컬 미리보기와 이메일 본문에 동일 템플릿 재사용)."""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.fetchers.base import NewsItem

_TEMPLATE_NAME = "digest.html.j2"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

_SENTENCE_END = re.compile(r"[.!?다요]\s")


def _truncate_display(text: str | None, limit: int, search_from: int = 60) -> str:
    """이메일 표시용으로만 텍스트를 자른다(LLM 입력이나 저장용 원문은 건드리지 않음).

    search_from~limit 구간에서 문장 종결부를 찾아 자연스럽게 끊고, 없으면 limit에서
    하드컷 후 "…"을 붙인다.
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    matches = list(_SENTENCE_END.finditer(window, search_from))
    if matches:
        return window[: matches[-1].end() - 1].rstrip()
    return window.rstrip() + "…"


def _get_env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)
    env.filters["truncate_display"] = _truncate_display
    return env


def build_html(
    items_by_keyword: "OrderedDict[str, list[NewsItem]]",
    generated_at: datetime,
    subject: str = "주요뉴스 다이제스트",
) -> str:
    env = _get_env()
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(
        items_by_keyword=items_by_keyword,
        generated_at=generated_at.strftime("%Y-%m-%d (%a) %H:%M"),
        subject=subject,
    )


def save_html(html: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = output_dir / filename
    path.write_text(html, encoding="utf-8")
    return path
