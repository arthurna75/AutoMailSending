"""HTML 다이제스트 생성 (로컬 미리보기와 이메일 본문에 동일 템플릿 재사용)."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.fetchers.base import NewsItem

_TEMPLATE_NAME = "digest.html.j2"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _get_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


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
