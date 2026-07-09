# 운영 관리 가이드 (내가 계속 챙겨야 할 것들)

이 문서는 코드/설정을 다 갖춰놓은 뒤에도 **운영자(나)가 직접, 반복적으로 관리해야 하는 부분**만 정리한
것입니다. 처음 셋업 방법은 `README.md` 참고.

---

## 1. 사용할 사람 초대 (가장 자주 할 일)

회원가입을 막아뒀기 때문에, **새로 쓸 사람이 생길 때마다 아래 절차를 직접 해줘야** 로그인이 가능합니다.

1. Supabase 대시보드 → **Authentication → Users → Add user → Invite user**
2. 초대할 이메일 입력 → 전송
3. 그 사람은 이후 `https://web-psi-rouge-56.vercel.app/login`에서 같은 이메일로 **인증 코드 로그인**을 스스로 진행하면 됨(추가로 내가 해줄 건 없음)
4. 처음 로그인하면 `/dashboard`에서 본인 키워드/발송시각을 직접 설정 → 자동으로 매일 다이제스트 수신 시작

> 탈퇴/이용 중지시키고 싶으면: Supabase → Authentication → Users에서 해당 계정 삭제, 또는 `user_settings.is_active`를 `false`로 바꾸면 로그인은 되지만 다이제스트는 더 이상 안 나감.

---

## 2. 시크릿/환경변수 — 갱신이 필요할 때

아래 값들은 전부 **내 개인 계정 자격증명을 서비스 전체가 공유**하는 구조입니다(사용자별로 따로 안 받음).
비밀번호를 바꾸거나 키를 재발급받으면 반드시 아래 두 군데를 갱신해야 합니다.

| 값 | 어디서 재발급 | 어디에 등록 |
|---|---|---|
| Gmail 앱 비밀번호 (`SMTP_PASSWORD`) | myaccount.google.com/apppasswords | GitHub Secrets |
| Naver API 키 (`NAVER_CLIENT_ID/SECRET`) | developers.naver.com | GitHub Secrets |
| OpenAI API 키 (`OPENAI_API_KEY`) | platform.openai.com/api-keys | GitHub Secrets |
| Supabase `service_role`(Secret key) | Supabase → Project Settings → API | GitHub Secrets (`SUPABASE_SERVICE_ROLE_KEY`) |
| Supabase `publishable`(anon) key | Supabase → Project Settings → API | Vercel 환경변수 + `web/.env.local`(로컬용) |
| GitHub 워크플로우 트리거용 토큰 (`GITHUB_DISPATCH_TOKEN`) | GitHub → Settings → Developer settings → Fine-grained tokens (이 저장소 한정, "Actions: Read and write" 권한만) | Vercel 환경변수 (서버 전용, `NEXT_PUBLIC_` 접두어 없이) |

**GitHub Secrets 등록 위치**: `https://github.com/arthurna75/AutoMailSending/settings/secrets/actions`
**Vercel 환경변수 등록 위치**: Vercel 대시보드 → 프로젝트 `web` → Settings → Environment Variables
(둘 다 값을 바꾼 뒤에는 워커/웹앱을 다시 실행·배포해야 반영됩니다 — GitHub Actions는 다음 실행부터 자동 반영, Vercel은 재배포 필요.)

---

## 3. Supabase 대시보드에서 유지해야 하는 설정

한 번 맞춰두면 평소엔 안 건드려도 되지만, **뭔가 안 될 때 가장 먼저 확인할 곳**입니다.

- **Authentication → Providers → Email → "Allow new users to sign up"**: 반드시 **꺼짐** 상태 유지 (켜지면 아무나 가입 가능해짐)
- **Authentication → Emails → "Magic Link" 템플릿**: 클릭 링크 없이 `{{ .Token }}` 코드만 있어야 함 (링크가 있으면 메일 보안 스캐너가 미리 소모해서 로그인 실패할 수 있음 — 실제 겪었던 문제)
- **Authentication → URL Configuration → Redirect URLs**: `http://localhost:3000/**`, `https://web-psi-rouge-56.vercel.app/**` 등록되어 있어야 함 (로그인 자체는 이제 리다이렉트를 안 쓰지만, 나중에 다른 로그인 방식을 추가할 경우를 대비해 유지)
- **Authentication → SMTP Settings**: 내 Gmail 계정으로 커스텀 SMTP 등록되어 있어야 함 (Supabase 기본 메일 발송은 rate limit이 매우 낮아서 꺼두면 로그인 코드 발송이 자주 막힘)

---

## 4. 새로 배포할 때 (코드 수정 후)

- **웹(web/) 코드 수정 시**: `cd web && vercel --prod --yes` 로 재배포 (회사 PC망에서는 SSL 검사 때문에 아래 환경변수를 먼저 설정해야 vercel 명령이 동작함)
  ```
  export NODE_EXTRA_CA_CERTS=/tmp/corp-ca-bundle.pem
  ```
  (이 파일이 없다면 Windows 인증서 저장소에서 새로 내보내야 함 — PowerShell로 `Cert:\LocalMachine\Root`, `Cert:\CurrentUser\Root`를 PEM으로 export)
- **워커(worker/) 코드 수정 시**: 별도 배포 불필요. `git push`만 하면 다음 GitHub Actions 실행부터 자동 반영됨.
- **DB 스키마 변경(마이그레이션 파일 추가) 시**: `git push`만으로는 적용되지 않음. `supabase/migrations/`에 새 `.sql` 파일을 커밋한 뒤, Supabase 대시보드 → SQL Editor에서 그 파일 내용을 직접 실행해야 함.
- **수동으로 지금 당장 테스트하고 싶을 때**: GitHub → Actions → `news-digest-worker` → Run workflow
  - `dry_run: true` → 발송 없이 로그만 확인
  - `force: true` → 발송 시각 창 무시하고 즉시 처리
  - `test_send: true` → 실제 메일은 보내되 발송 이력(`last_sent_date`/`sent_articles`/`digests`)은 안 남김(`user_id` 필수)
  - `user_id` → 특정 사용자 1명만 테스트
- 이제 사용자는 이 GitHub UI를 몰라도 **대시보드의 "지금 테스트 메일 받기" 버튼**으로 본인 몫만 스스로 테스트할 수 있음(내부적으로 `web/app/api/test-send/route.ts`가 위 `test_send` 입력으로 GitHub API를 대신 호출해줌 — `GITHUB_DISPATCH_TOKEN`이 Vercel에 등록되어 있어야 동작함).
- 이 버튼은 대시보드에 **저장하지 않은 채 화면에 입력 중인 값**도 `settings_json` 입력으로 함께 실어 보냄 — 워커는 `TEST_SETTINGS_JSON` 환경변수가 있으면 Supabase `user_settings` 조회 없이 그 값으로만 발송함(`worker/main.py`). 사용자별 자유 입력값이라 워크플로우 스크립트에는 `${{ }}` 인라인 치환 없이 `env:` 경유로만 전달함(스크립트 인젝션 방지).

---

## 5. 평소 모니터링

- **발송이 잘 되고 있는지**: GitHub → Actions 탭에서 15분마다 도는 `news-digest-worker` 실행 로그 확인 (초록 체크면 정상)
- **누가 언제 뭘 받았는지**: Supabase Table Editor → `digests`(발송 헤더), `sent_articles`(기사별 이력)
- **워커 실행 통계**: Supabase Table Editor → `worker_runs` (처리된 사용자 수, LLM 호출 수, 토큰 사용량 등 — 현재 비용 상한 로직은 없으므로 참고용으로만 봄). LLM 호출 수에는 요약뿐 아니라 키워드 관련성 필터 호출도 합산됨(아래 참고).
- **OpenAI 비용**: platform.openai.com/usage 에서 직접 확인 (토큰 절약 로직을 의도적으로 뺐으므로, 사용자가 늘면 여기서 실제 비용을 주기적으로 확인하는 게 좋음)

---

## 6. 알아두면 좋은 제약/설계 결정

- 크롤링(`worker/src/fetchers/crawler.py`)은 API/RSS 요약이 부실할 때 본문을 보강하는 용도로만 씀 — API가 아예 없는 새 뉴스 소스를 추가하려면 별도 개발 필요.
- LLM 요약은 기사당 1회씩 개별 호출(비용보다 신뢰성 우선으로 설계 변경함) — 사용자/기사 수가 많이 늘면 OpenAI 비용이 비례해서 늘어남.
- 발송은 하루 1회, 사용자가 설정한 시각이 지나면 그날 안에는 언제 실행되든 반드시 캐치업 발송(중복 발송은 안 됨).
- 로그인은 매직링크가 아니라 **이메일 코드 입력 방식** — 회사 메일 보안 스캐너 때문에 링크 클릭 방식은 신뢰할 수 없다고 판단해 의도적으로 이렇게 설계함.
- 키워드 동음이의어 필터(`worker/src/filtering/`)는 사용자가 키워드 태그에 의도 힌트를 등록했을 때만 동작함 — 힌트가 없는 키워드는 LLM 호출 없이 기존처럼 전부 통과(비용 미증가). API 오류/응답 파싱 실패 시에는 fail-open(해당 키워드 기사를 전부 유지)으로 설계함 — 관련 기사를 놓치는 것보다 가끔 무관한 기사가 섞이는 쪽을 택함.

---

## 7. 사용자 문의 대응 Q&A

### Q. "키워드 N개 요청했는데 적게 왔다"는 문의를 받으면?

버그가 아니라 의도 힌트 필터(`worker/src/filtering/relevance_filter.py`)가 캡(`cap_items`)보다 먼저 적용되는 정상 동작일 가능성이 높음 — 그날 실제로 의도에 맞는 기사 자체가 적었던 것.

- **확인 방법**: GitHub → Actions → `news-digest-worker` → Run workflow에서 `dry_run:true` + `verbose:true`로 수동 실행해 로그에서 해당 키워드의 수집/필터 통과 건수 확인. 또는 Supabase `worker_runs`의 `llm_calls`로 필터가 실제로 호출됐는지 확인(5절 참고).
- **사용자 안내**: 태그를 다시 클릭해 의도 설명을 조금 더 넓게 고쳐쓰거나, 아예 비워서 필터링 없이 받아보게 하거나, 키워드당/전체 최대 개수 자체를 늘려보라고 안내(user_guide.html의 동일 Q&A 참고).

### Q. "발송 시각이 안 맞는다"는 문의를 받으면?

원인은 두 가지가 겹치는 경우가 대부분:

- GitHub Actions `schedule` 트리거는 정각(`:00/:15/:30/:45`) 슬롯이 전 세계적으로 몰려 지연되는 경우가 있음 — 플랫폼 자체 제약이라 코드로 해결 불가.
- 🎯 의도 설명이 있는 키워드가 있으면 AI 분석 처리 시간이 4~5분 정도 추가됨.

**확인 방법**: GitHub → Actions 탭에서 해당 시간대 실행의 실제 시작/종료 시각을 확인.

> 참고: 지연이 반복적으로 심해지면 `.github/workflows/worker.yml`의 cron 분(minute)을 정각에서 벗어난 값(예: `3,18,33,48`)으로 바꿔 혼잡한 정각 슬롯을 피하는 완화책이 있음. 다만 아직 적용하지 않았고, 필요해지면 별도로 진행할 것.

---

## 변경 이력

- 2026-07-07: 최초 작성 (사용자 초대, 시크릿 갱신, Supabase 설정, 배포, 모니터링, 설계 결정 정리).
- 2026-07-07: "지금 테스트 메일 받기" 기능 추가에 맞춰 `GITHUB_DISPATCH_TOKEN` 시크릿 항목과 `test_send` 워크플로우 입력 설명 추가.
- 2026-07-07: "지금 테스트 메일 받기"가 저장 전 화면 값을 `settings_json`으로 실어 보내도록 바뀐 점과 그에 따른 워크플로우 인젝션 방지 설계 추가.
- 2026-07-08: 키워드 동음이의어 구분(의도 힌트 + LLM 제목 관련성 필터) 기능 추가. `supabase/migrations/0002_keyword_hints.sql` 신규 — DB 마이그레이션은 `git push`만으로 자동 적용되지 않으므로 Supabase SQL Editor에서 직접 실행 필요.
- 2026-07-09: 키워드 개수 문의/발송 지연 문의 대응 Q&A 절 추가.
