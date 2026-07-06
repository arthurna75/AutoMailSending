"""애플리케이션 설정 로딩 (Supabase user_settings 1행 + 환경변수 -> AppConfig).

Naver API 키, Gmail SMTP 계정, OpenAI API 키는 모든 사용자가 공유하는 서비스 전체
자격증명이므로 환경변수(GitHub Actions Secrets)에서 읽는다. 사용자별로 다른 값은
keywords/counts/schedule/source-toggle/to_email 등 user_settings 행의 컬럼뿐이다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    """설정 값이 없거나 잘못된 경우."""


@dataclass
class NaverSourceConfig:
    enabled: bool = True
    client_id: str = ""
    client_secret: str = ""
    sort: str = "date"
    fetch_count: int = 20


@dataclass
class GoogleSourceConfig:
    enabled: bool = True
    hl: str = "ko"
    gl: str = "KR"
    ceid: str = "KR:ko"
    fetch_count: int = 20


@dataclass
class SourcesConfig:
    naver: NaverSourceConfig = field(default_factory=NaverSourceConfig)
    google: GoogleSourceConfig = field(default_factory=GoogleSourceConfig)


@dataclass
class DedupConfig:
    title_similarity_threshold: float = 0.85


@dataclass
class CountsConfig:
    per_keyword: int = 5
    total: int = 20


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    use_ssl: bool = False
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_addr: str = ""
    from_name: str = ""
    to_addrs: list[str] = field(default_factory=list)
    subject_template: str = "[주요뉴스] {date} 아침 다이제스트"


@dataclass
class CrawlConfig:
    enabled: bool = True


@dataclass
class LlmConfig:
    enabled: bool = True
    model: str = "gpt-4o-mini"
    max_daily_cost_usd: float = 0.5


@dataclass
class AppConfig:
    user_id: str = ""
    keywords: list[str] = field(default_factory=list)
    counts: CountsConfig = field(default_factory=CountsConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    dedup: DedupConfig = field(default_factory=DedupConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    subject_template: str = "[주요뉴스] {date} 아침 다이제스트"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def build_shared_email_config(to_addrs: list[str], subject_template: str) -> EmailConfig:
    """모든 사용자가 공유하는 발신 계정(Gmail SMTP)에 사용자별 수신 주소만 얹는다."""
    username = _env("SMTP_USERNAME")
    return EmailConfig(
        smtp_host=_env("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(_env("SMTP_PORT", "587")),
        use_ssl=_env("SMTP_USE_SSL", "false").lower() == "true",
        use_tls=_env("SMTP_USE_TLS", "true").lower() == "true",
        username=username,
        password=_env("SMTP_PASSWORD"),
        from_addr=_env("SMTP_FROM_ADDR", username),
        from_name=_env("SMTP_FROM_NAME", "주요뉴스 알리미"),
        to_addrs=to_addrs,
        subject_template=subject_template,
    )


def load_user_config(row: dict, account_email: str) -> AppConfig:
    """Supabase `user_settings` 1행(dict) -> AppConfig.

    row는 supabase-py로 조회한 딕셔너리(테이블 컬럼명 그대로), account_email은
    row.to_email이 비어있을 때 대체로 쓸 auth.users.email이다.
    """
    keywords = row.get("keywords") or []
    if not keywords:
        raise ConfigError(f"user_id={row.get('user_id')}: keywords가 비어 있습니다.")

    to_email = row.get("to_email") or account_email
    if not to_email:
        raise ConfigError(f"user_id={row.get('user_id')}: 수신 이메일을 확인할 수 없습니다.")

    subject_template = row.get("subject_template") or "[주요뉴스] {date} 아침 다이제스트"

    naver = NaverSourceConfig(
        enabled=bool(row.get("source_naver_enabled", True)),
        client_id=_env("NAVER_CLIENT_ID"),
        client_secret=_env("NAVER_CLIENT_SECRET"),
        sort="date",
        fetch_count=int(row.get("naver_fetch_count", 20)),
    )
    google = GoogleSourceConfig(
        enabled=bool(row.get("source_google_enabled", True)),
        fetch_count=int(row.get("google_fetch_count", 20)),
    )
    if naver.enabled and (not naver.client_id or not naver.client_secret):
        raise ConfigError(
            "NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 환경변수(GitHub Actions Secrets)가 비어 있습니다."
        )

    return AppConfig(
        user_id=row["user_id"],
        keywords=list(keywords),
        counts=CountsConfig(
            per_keyword=int(row.get("per_keyword_count", 5)),
            total=int(row.get("total_count", 20)),
        ),
        sources=SourcesConfig(naver=naver, google=google),
        dedup=DedupConfig(title_similarity_threshold=float(row.get("dedup_threshold", 0.85))),
        email=build_shared_email_config([to_email], subject_template),
        crawl=CrawlConfig(enabled=bool(row.get("crawl_enabled", True))),
        llm=LlmConfig(
            enabled=bool(row.get("llm_summary_enabled", True)),
            model=_env("OPENAI_MODEL", "gpt-4o-mini"),
            max_daily_cost_usd=float(_env("MAX_DAILY_LLM_COST_USD", "0.5")),
        ),
        subject_template=subject_template,
    )
