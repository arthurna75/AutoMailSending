-- 접근 요청(가입 신청) 관리: 신규 이메일은 즉시 Auth 계정을 만들지 않고 이 테이블에만 기록해두고,
-- 운영자가 /admin 화면에서 승인해야 비로소 Supabase Auth 사용자가 생성된다.

create table if not exists signup_requests (
  id bigserial primary key,
  email text not null unique,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  requested_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create index if not exists signup_requests_status_idx on signup_requests (status, requested_at);

alter table signup_requests enable row level security;
-- 정책 없음: anon/authenticated는 접근 불가, API 라우트의 service_role 키만 RLS를 우회해 접근
