"""중복 제거 및 개수 제한 로직."""

from __future__ import annotations

import difflib
import html
import re
from collections import OrderedDict
from typing import Iterable, Optional

from src.fetchers.base import NewsItem

_TAG_RE = re.compile(r"<[^>]+>")
_NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z가-힣\s]")


def normalize_title(title: str) -> str:
    without_tags = _TAG_RE.sub("", title)
    unescaped = html.unescape(without_tags)
    no_punct = _NON_ALNUM_RE.sub("", unescaped)
    return " ".join(no_punct.split()).casefold()


def dedup_items(
    items: list[NewsItem],
    threshold: float,
    seen_links: Optional[set[str]] = None,
) -> list[NewsItem]:
    kept: list[NewsItem] = []
    kept_norm_titles: list[str] = []
    kept_links: set[str] = set()

    for item in items:
        if seen_links and item.link in seen_links:
            continue
        if item.link in kept_links:
            continue

        norm_title = normalize_title(item.title)
        is_duplicate = any(
            difflib.SequenceMatcher(None, norm_title, existing).ratio() >= threshold
            for existing in kept_norm_titles
        )
        if is_duplicate:
            continue

        kept.append(item)
        kept_norm_titles.append(norm_title)
        kept_links.add(item.link)

    return kept


def cap_items(items: Iterable[NewsItem], per_keyword: int, total: int) -> list[NewsItem]:
    groups: "OrderedDict[str, list[NewsItem]]" = OrderedDict()
    for item in items:
        groups.setdefault(item.keyword, []).append(item)

    for keyword, group in groups.items():
        groups[keyword] = group[:per_keyword]

    result: list[NewsItem] = []
    queues = {keyword: list(group) for keyword, group in groups.items()}
    while len(result) < total and any(queues.values()):
        for keyword in list(queues.keys()):
            if len(result) >= total:
                break
            queue = queues[keyword]
            if queue:
                result.append(queue.pop(0))

    return result


def group_by_keyword(items: Iterable[NewsItem]) -> "OrderedDict[str, list[NewsItem]]":
    groups: "OrderedDict[str, list[NewsItem]]" = OrderedDict()
    for item in items:
        groups.setdefault(item.keyword, []).append(item)
    return groups
