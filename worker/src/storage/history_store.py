"""발송 이력 저장소.

JSON 파일 구현을 기본으로 두되, 향후 DB(SQLite/Postgres)로 교체할 때 fetchers/aggregator/
mailer/report 어느 것도 건드리지 않도록 HistoryStore 추상 인터페이스로 분리한다.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


class HistoryStore(ABC):
    @abstractmethod
    def has_seen(self, link: str) -> bool:
        ...

    @abstractmethod
    def seen_links(self) -> set[str]:
        ...

    @abstractmethod
    def mark_seen(self, links: Iterable[str], as_of: datetime) -> None:
        ...

    @abstractmethod
    def prune(self, retention_days: int) -> None:
        ...


class JsonFileHistoryStore(HistoryStore):
    """{"link": "ISO8601 타임스탬프", ...} 형태로 저장하는 단순 파일 기반 구현."""

    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("이력 파일을 읽을 수 없어 새로 시작합니다: %s", self._path)
            self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def has_seen(self, link: str) -> bool:
        return link in self._data

    def seen_links(self) -> set[str]:
        return set(self._data.keys())

    def mark_seen(self, links: Iterable[str], as_of: datetime) -> None:
        timestamp = as_of.isoformat()
        for link in links:
            self._data[link] = timestamp
        self._save()

    def prune(self, retention_days: int) -> None:
        if retention_days <= 0:
            return
        cutoff = datetime.now() - timedelta(days=retention_days)
        kept = {}
        for link, timestamp in self._data.items():
            try:
                seen_at = datetime.fromisoformat(timestamp)
            except ValueError:
                continue
            if seen_at >= cutoff:
                kept[link] = timestamp
        if len(kept) != len(self._data):
            self._data = kept
            self._save()
