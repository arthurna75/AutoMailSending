"""주요뉴스 자동화 메일전송 워커 - 온라인(멀티유저) 진입점.

흐름(사용자별): 설정 로드 -> 네이버/구글 수집 -> 중복 제거/개수 제한
     -> 크롤링으로 본문 보강 -> LLM 요약 -> HTML 생성 -> 이메일 발송 -> 발송 이력 기록

GitHub Actions에서 15분 간격으로 실행되며, 매 실행마다 "지금 발송해야 할 사용자"만
골라서 처리한다(사용자별 타임존의 로컬 시각 + last_sent_date로 판단, 재실행/지연에
안전하도록 멱등적으로 동작).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from src.aggregation.aggregator import cap_items, dedup_items, group_by_keyword
from src.app_config import AppConfig, ConfigError, load_user_config
from src.expansion.keyword_expansion import related_keywords_via_llm, split_keyword_tokens
from src.fetchers.base import NewsItem
from src.fetchers.crawler import enrich_with_crawled_content
from src.fetchers.google_rss import GoogleNewsRssFetcher
from src.fetchers.naver import NaverNewsFetcher
from src.filtering.relevance_filter import FilterUsage, filter_by_relevance
from src.mailer.smtp_mailer import SmtpMailer
from src.report.builder import build_html, save_html
from src.storage.supabase_history_store import SupabaseHistoryStore
from src.summarize.cache import fetch_cached_rows, url_hash
from src.summarize.llm_summarizer import summarize_items
from src.supabase_client import get_supabase_client
from src.utils.logging_setup import configure_logging

logger = logging.getLogger(__name__)

_HISTORY_RETENTION_DAYS = 14


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="주요뉴스 자동화 메일전송 워커")
    parser.add_argument("--dry-run", action="store_true", help="이메일 발송/이력 기록 없이 수집~HTML 생성만 수행")
    parser.add_argument("--user-id", type=str, default=None, help="특정 사용자 1명만 처리(테스트용)")
    parser.add_argument("--force", action="store_true", help="발송 시각 창을 무시하고 즉시 처리(테스트용)")
    parser.add_argument(
        "--test-send",
        action="store_true",
        help="실제 메일은 보내되 발송 이력(last_sent_date/sent_articles/digests)은 남기지 않는 미리보기 발송. --user-id 필수.",
    )
    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")
    args = parser.parse_args(argv)
    if args.test_send and not args.user_id:
        parser.error("--test-send는 --user-id와 함께 사용해야 합니다.")
    return args


def _is_due_now(row: dict, now_utc: datetime, force: bool) -> bool:
    if force:
        return True
    tz = ZoneInfo(row.get("timezone") or "Asia/Seoul")
    local_now = now_utc.astimezone(tz)
    if str(row.get("last_sent_date")) == local_now.date().isoformat():
        return False

    send_time = str(row["send_time"])  # Supabase가 "HH:MM:SS" 문자열로 반환
    send_hour, send_minute = int(send_time[:2]), int(send_time[3:5])
    target_minutes = send_hour * 60 + send_minute
    now_minutes = local_now.hour * 60 + local_now.minute
    # 상한을 두지 않는다: cron이 지연되어도(예: 15분 이상) 그날 안에는 반드시 캐치업해서
    # 발송한다. last_sent_date 가드가 있어 하루 중복 발송은 여전히 방지된다.
    return now_minutes >= target_minutes


def _build_fetchers(cfg: AppConfig) -> tuple[Optional[NaverNewsFetcher], Optional[GoogleNewsRssFetcher]]:
    naver_fetcher = None
    if cfg.sources.naver.enabled:
        naver_fetcher = NaverNewsFetcher(
            client_id=cfg.sources.naver.client_id,
            client_secret=cfg.sources.naver.client_secret,
            sort=cfg.sources.naver.sort,
        )
    google_fetcher = None
    if cfg.sources.google.enabled:
        google_fetcher = GoogleNewsRssFetcher(
            hl=cfg.sources.google.hl, gl=cfg.sources.google.gl, ceid=cfg.sources.google.ceid
        )
    return naver_fetcher, google_fetcher


def _collect_items(
    cfg: AppConfig,
    naver_fetcher: Optional[NaverNewsFetcher],
    google_fetcher: Optional[GoogleNewsRssFetcher],
) -> list[NewsItem]:
    all_items: list[NewsItem] = []

    for keyword in cfg.keywords:
        if naver_fetcher is not None:
            try:
                all_items.extend(naver_fetcher.fetch(keyword, cfg.sources.naver.fetch_count))
            except Exception:
                logger.exception("네이버 수집 중 오류 (keyword=%s)", keyword)
        if google_fetcher is not None:
            try:
                all_items.extend(google_fetcher.fetch(keyword, cfg.sources.google.fetch_count))
            except Exception:
                logger.exception("구글 수집 중 오류 (keyword=%s)", keyword)

    return all_items


def _fetch_terms(
    terms: list[str],
    original_keyword: str,
    count: int,
    naver_fetcher: Optional[NaverNewsFetcher],
    google_fetcher: Optional[GoogleNewsRssFetcher],
) -> list[NewsItem]:
    items: list[NewsItem] = []
    for term in terms:
        if naver_fetcher is not None:
            try:
                items.extend(naver_fetcher.fetch(term, count))
            except Exception:
                logger.exception("확장 검색 중 오류 (term=%s)", term)
        if google_fetcher is not None:
            try:
                items.extend(google_fetcher.fetch(term, count))
            except Exception:
                logger.exception("확장 검색 중 오류 (term=%s)", term)

    for item in items:
        item.keyword = original_keyword
    return items


def _expand_thin_keywords(
    cfg: AppConfig,
    deduped: list[NewsItem],
    naver_fetcher: Optional[NaverNewsFetcher],
    google_fetcher: Optional[GoogleNewsRssFetcher],
    seen_links: set[str],
    filter_usage: FilterUsage,
) -> list[NewsItem]:
    """복합 키워드의 발송 후보가 설정한 키워드당 개수에 못 미치면, 구성 단어/연관 검색어로
    재검색해 후보 풀을 넓힌다. 단일어 키워드나 이미 충분한 키워드는 추가 API 호출 없이 건너뛴다."""
    groups = group_by_keyword(deduped)
    expand_count = max(cfg.counts.per_keyword * 2, 10)
    extra_items: list[NewsItem] = []

    for keyword in cfg.keywords:
        current = groups.get(keyword, [])
        if len(current) >= cfg.counts.per_keyword:
            continue

        tokens = split_keyword_tokens(keyword)
        if len(tokens) < 2:
            continue

        sub_items = _fetch_terms(tokens, keyword, expand_count, naver_fetcher, google_fetcher)

        if len(current) + len(sub_items) < cfg.counts.per_keyword and cfg.llm.enabled:
            related, related_usage = related_keywords_via_llm(keyword, tokens, cfg.llm.model)
            filter_usage.llm_calls += related_usage.llm_calls
            filter_usage.prompt_tokens += related_usage.prompt_tokens
            filter_usage.completion_tokens += related_usage.completion_tokens
            if related:
                sub_items += _fetch_terms(related, keyword, expand_count, naver_fetcher, google_fetcher)

        if not sub_items:
            continue

        hint = cfg.keyword_hints.get(keyword, "")
        if hint:
            sub_items, hint_usage = filter_by_relevance(sub_items, {keyword: hint}, cfg.llm.model)
            filter_usage.llm_calls += hint_usage.llm_calls
            filter_usage.prompt_tokens += hint_usage.prompt_tokens
            filter_usage.completion_tokens += hint_usage.completion_tokens

        logger.info(
            "키워드 확장: keyword=%s 기존=%d건, 토큰/연관어 검색으로 %d건 추가 후보 확보",
            keyword, len(current), len(sub_items),
        )
        extra_items.extend(sub_items)

    if not extra_items:
        return deduped

    return dedup_items(deduped + extra_items, cfg.dedup.title_similarity_threshold, seen_links=seen_links)


def process_user(supabase, row: dict, now_utc: datetime, dry_run: bool, test_send: bool = False) -> dict:
    cfg = load_user_config(row, account_email=row.get("_account_email", ""))

    history = SupabaseHistoryStore(supabase, cfg.user_id)
    history.prune(_HISTORY_RETENTION_DAYS)
    seen_links = history.seen_links()

    naver_fetcher, google_fetcher = _build_fetchers(cfg)

    fetched = _collect_items(cfg, naver_fetcher, google_fetcher)
    deduped = dedup_items(fetched, cfg.dedup.title_similarity_threshold, seen_links=seen_links)

    if cfg.llm.enabled and cfg.keyword_hints:
        deduped, filter_usage = filter_by_relevance(deduped, cfg.keyword_hints, cfg.llm.model)
    else:
        filter_usage = FilterUsage()

    deduped = _expand_thin_keywords(cfg, deduped, naver_fetcher, google_fetcher, seen_links, filter_usage)

    capped = cap_items(deduped, cfg.counts.per_keyword, cfg.counts.total)

    stats = {
        "fetched": len(fetched), "sent": len(capped),
        "llm_calls": filter_usage.llm_calls, "llm_cache_hits": 0,
        "prompt_tokens": filter_usage.prompt_tokens, "completion_tokens": filter_usage.completion_tokens,
    }

    if not capped:
        logger.info("user_id=%s: 발송할 새 기사가 없어 건너뜁니다.", cfg.user_id)
        return stats

    if cfg.crawl.enabled:
        cache_rows = fetch_cached_rows(supabase, [url_hash(i.link) for i in capped])

        def _lookup(link: str):
            cached = cache_rows.get(url_hash(link))
            return cached.get("crawled_content") if cached else None

        def _store(link: str, content: str) -> None:
            pass  # 크롤링 결과는 summarize_items()가 article_cache upsert 시 함께 저장한다

        enrich_with_crawled_content(capped, _lookup, _store)

    if cfg.llm.enabled:
        usage = summarize_items(capped, supabase, cfg.llm.model)
        stats["llm_calls"] += usage.llm_calls
        stats["llm_cache_hits"] += usage.cache_hits
        stats["prompt_tokens"] += usage.prompt_tokens
        stats["completion_tokens"] += usage.completion_tokens

    items_by_keyword = group_by_keyword(capped)
    tz = ZoneInfo(row.get("timezone") or "Asia/Seoul")
    generated_at = now_utc.astimezone(tz)
    subject = cfg.subject_template.format(date=generated_at.strftime("%Y-%m-%d"))
    html = build_html(items_by_keyword, generated_at, subject=subject)

    if dry_run:
        path = save_html(html, Path("output"))
        logger.info("user_id=%s: --dry-run, HTML만 저장: %s", cfg.user_id, path)
        return stats

    SmtpMailer(cfg.email).send(subject, html, cfg.email.to_addrs)

    if test_send:
        logger.info("user_id=%s: 테스트 발송 완료 (이력 기록 없음, 기사 %d건)", cfg.user_id, len(capped))
        return stats

    history.mark_seen([item.link for item in capped], generated_at)

    supabase.table("digests").insert(
        {"user_id": cfg.user_id, "subject": subject, "article_count": len(capped)}
    ).execute()
    supabase.table("user_settings").update(
        {"last_sent_date": generated_at.date().isoformat()}
    ).eq("user_id", cfg.user_id).execute()

    logger.info("user_id=%s: 발송 완료 (기사 %d건)", cfg.user_id, len(capped))
    return stats


def _account_emails(supabase) -> dict[str, str]:
    users = supabase.auth.admin.list_users()
    return {u.id: u.email for u in users if getattr(u, "email", None)}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(verbose=args.verbose)

    supabase = get_supabase_client()
    now_utc = datetime.now(ZoneInfo("UTC"))

    override_settings_json = os.environ.get("TEST_SETTINGS_JSON") if args.test_send else None
    if override_settings_json:
        override_row = json.loads(override_settings_json)
        override_row["user_id"] = args.user_id
        rows = [override_row]
    else:
        query = supabase.table("user_settings").select("*").eq("is_active", True)
        if args.user_id:
            query = query.eq("user_id", args.user_id)
        rows = query.execute().data

    emails_by_user_id = _account_emails(supabase)

    run_totals = {
        "users_processed": 0, "articles_fetched": 0, "articles_sent": 0,
        "llm_calls": 0, "llm_cache_hits": 0,
        "prompt_tokens": 0, "completion_tokens": 0,
    }

    for row in rows:
        if not _is_due_now(row, now_utc, force=args.force or args.test_send):
            continue
        row["_account_email"] = emails_by_user_id.get(row["user_id"], "")

        try:
            stats = process_user(supabase, row, now_utc, dry_run=args.dry_run, test_send=args.test_send)
        except ConfigError as e:
            logger.error("user_id=%s 설정 오류: %s", row["user_id"], e)
            continue
        except Exception:
            logger.exception("user_id=%s 처리 중 오류", row["user_id"])
            continue

        run_totals["users_processed"] += 1
        run_totals["articles_fetched"] += stats["fetched"]
        run_totals["articles_sent"] += stats["sent"]
        run_totals["llm_calls"] += stats["llm_calls"]
        run_totals["llm_cache_hits"] += stats["llm_cache_hits"]
        run_totals["prompt_tokens"] += stats["prompt_tokens"]
        run_totals["completion_tokens"] += stats["completion_tokens"]

    if not args.dry_run:
        supabase.table("worker_runs").insert(
            {
                "finished_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "users_processed": run_totals["users_processed"],
                "articles_fetched": run_totals["articles_fetched"],
                "articles_sent": run_totals["articles_sent"],
                "llm_calls": run_totals["llm_calls"],
                "llm_cache_hits": run_totals["llm_cache_hits"],
                "total_prompt_tokens": run_totals["prompt_tokens"],
                "total_completion_tokens": run_totals["completion_tokens"],
                "status": "ok",
            }
        ).execute()

    logger.info("워커 실행 완료: %s", run_totals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
