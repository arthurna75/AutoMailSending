"""HistoryStore ABC의 Supabase 구현체 — sent_articles 테이블 기반, 사용자별 발송 이력.

기존 JsonFileHistoryStore를 대체하지만 aggregator/mailer/report는 ABC 시그니처만
알고 있으므로 전혀 손댈 필요가 없다."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from src.storage.history_store import HistoryStore
from src.summarize.cache import url_hash


class SupabaseHistoryStore(HistoryStore):
    def __init__(self, supabase, user_id: str):
        self._supabase = supabase
        self._user_id = user_id
        self._seen: set[str] | None = None

    def _load(self) -> set[str]:
        if self._seen is None:
            resp = (
                self._supabase.table("sent_articles")
                .select("url")
                .eq("user_id", self._user_id)
                .execute()
            )
            self._seen = {row["url"] for row in resp.data}
        return self._seen

    def has_seen(self, link: str) -> bool:
        return link in self._load()

    def seen_links(self) -> set[str]:
        return set(self._load())

    def mark_seen(self, links: Iterable[str], as_of: datetime) -> None:
        rows = [
            {
                "user_id": self._user_id,
                "url": link,
                "url_hash": url_hash(link),
                "sent_at": as_of.isoformat(),
            }
            for link in links
        ]
        if rows:
            self._supabase.table("sent_articles").insert(rows).execute()
        self._seen = None

    def prune(self, retention_days: int) -> None:
        if retention_days <= 0:
            return
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        (
            self._supabase.table("sent_articles")
            .delete()
            .eq("user_id", self._user_id)
            .lt("sent_at", cutoff)
            .execute()
        )
