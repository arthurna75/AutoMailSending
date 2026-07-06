-- 뉴스 다이제스트 온라인 전환 - 초기 스키마
-- 사용자별 설정, 전역 기사 요약 캐시(토큰 절약 핵심), 발송 이력, 실행/비용 로그

create table if not exists user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  keywords text[] not null default '{}',
  per_keyword_count int not null default 5,
  total_count int not null default 20,
  dedup_threshold numeric not null default 0.85,
  source_naver_enabled boolean not null default true,
  source_google_enabled boolean not null default true,
  naver_fetch_count int not null default 20,
  google_fetch_count int not null default 20,
  crawl_enabled boolean not null default true,
  llm_summary_enabled boolean not null default true,
  to_email text,
  subject_template text default '[주요뉴스] {date} 아침 다이제스트',
  timezone text not null default 'Asia/Seoul',
  send_time time not null default '07:00',
  is_active boolean not null default true,
  last_sent_date date,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table user_settings enable row level security;

drop policy if exists "own row" on user_settings;
create policy "own row" on user_settings
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 전역 공유 요약 캐시: 동일 URL이면 여러 사용자가 구독해도 크롤링/LLM 요약을 1회만 수행
create table if not exists article_cache (
  url_hash text primary key,
  url text not null,
  title text,
  raw_summary text,
  crawled_content text,
  llm_summary text,
  llm_model text,
  prompt_tokens int,
  completion_tokens int,
  summarized_at timestamptz,
  created_at timestamptz default now()
);

alter table article_cache enable row level security;
-- 정책 없음: anon/authenticated는 접근 불가, 워커(service_role 키)만 RLS를 우회해 접근

create table if not exists digests (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  sent_at timestamptz not null default now(),
  subject text,
  article_count int
);

alter table digests enable row level security;

drop policy if exists "own digests read" on digests;
create policy "own digests read" on digests
  for select using (auth.uid() = user_id);
-- insert 정책 없음: service_role(워커)만 기록

create table if not exists sent_articles (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  url text not null,
  url_hash text not null,
  title text,
  sent_at timestamptz not null default now()
);

create index if not exists sent_articles_user_hash_idx on sent_articles (user_id, url_hash);

alter table sent_articles enable row level security;

drop policy if exists "own sent read" on sent_articles;
create policy "own sent read" on sent_articles
  for select using (auth.uid() = user_id);

-- 실행/비용 모니터링 (일일 LLM 비용 상한 판단에 사용)
create table if not exists worker_runs (
  id bigserial primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  users_processed int,
  articles_fetched int,
  articles_sent int,
  llm_calls int,
  llm_cache_hits int,
  total_prompt_tokens int,
  total_completion_tokens int,
  estimated_cost_usd numeric,
  status text,
  error_message text
);

alter table worker_runs enable row level security;
-- 정책 없음: service_role(워커)만 접근
