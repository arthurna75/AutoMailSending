"""뉴스 API/RSS 응답에 섞여있는 HTML 태그·엔티티를 제거하는 유틸."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(raw: str) -> str:
    if not raw:
        return ""
    without_tags = _TAG_RE.sub("", raw)
    return html.unescape(without_tags).strip()


def clean_naver_text(raw: str) -> str:
    """네이버 검색 API의 <b> 강조 태그 및 엔티티 제거."""
    return strip_html(raw)
