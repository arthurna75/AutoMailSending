-- 키워드 동음이의어 구분: 키워드별 선택적 의도 힌트
-- 힌트가 있는 키워드에 한해 워커가 LLM으로 제목 관련성을 판단해 무관한 기사를 걸러낸다.

alter table user_settings add column if not exists keyword_hints jsonb not null default '{}'::jsonb;
