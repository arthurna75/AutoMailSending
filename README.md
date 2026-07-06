# 주요뉴스 다이제스트 (온라인)

키워드 기반으로 네이버·구글 뉴스를 자동 수집해 필요시 본문을 크롤링하고 OpenAI로 요약한 뒤,
사용자별로 설정한 시각에 이메일로 발송하는 멀티유저 온라인 서비스입니다.

- **웹 설정 UI** (`web/`, Next.js): 초대받은 사용자가 로그인해 키워드/발송시각/타임존/소스 설정
- **워커** (`worker/`, Python): GitHub Actions에서 15분 간격으로 실행되어 "지금 발송해야 할 사용자"만 처리
- **DB/Auth**: Supabase (Postgres + RLS + 매직링크 인증)

로컬 Windows 데스크톱 버전(`../자동뉴스 집계(로컬)`)의 후속 버전입니다. 기존 dedup/cap 로직,
`HistoryStore` 추상화, Jinja2 템플릿을 그대로 재사용했습니다.

## 아키텍처 한눈에 보기

```
사용자(웹, Vercel) --설정 저장--> Supabase(user_settings)
                                        │
GitHub Actions(15분 cron) --읽음--> worker/main.py
                                        │
                    Naver API / Google RSS 수집
                          │
                    dedup + cap (기존 로직 그대로)
                          │
              크롤링 본문 보강 (article_cache 우선 조회)
                          │
              OpenAI 배치 요약 (article_cache 우선 조회, 비용 상한)
                          │
                    HTML 생성 → Gmail SMTP 발송
                          │
              Supabase(digests/sent_articles/worker_runs) 기록
```

토큰/비용 절약 전략(핵심): dedup·cap **이후** 실제 발송될 기사에만 크롤링·LLM을 적용하고,
URL 해시 기준 전역 캐시(`article_cache`)를 공유해 여러 사용자가 같은 기사를 구독해도
크롤링/요약은 1회만 수행합니다. 자세한 내용은 `worker/src/summarize/llm_summarizer.py` 참고.

## 저장소 구조

```
web/       Next.js 설정 UI (Vercel 배포)
worker/    Python 워커 (GitHub Actions에서 실행)
supabase/  마이그레이션 SQL
.github/workflows/worker.yml   15분 간격 스케줄러
```

## 1. Supabase 설정

1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. SQL Editor에서 `supabase/migrations/0001_init.sql` 실행
3. Authentication → Providers → Email에서 **"Allow new users to sign up" 비활성화**
   (지인 몇 명만 쓰는 서비스이므로 회원가입을 막고, Authentication → Users → Invite user로 직접 초대)
4. Project Settings → API에서 URL, `anon` key(웹용), `service_role` key(워커용)를 확보

## 2. 시크릿 준비 (GitHub Actions Secrets에 등록)

| 이름 | 설명 |
|---|---|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | RLS를 우회하는 서비스 키 (워커 전용, 절대 프런트엔드에 노출 금지) |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | developers.naver.com에서 발급 (무료) |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | 발신용 Gmail 계정 + **앱 비밀번호**(일반 로그인 비밀번호 아님) |

⚠️ 기존 로컬 버전의 `config.yaml`에 있던 Gmail 앱 비밀번호와 Naver Client Secret은 반드시
**재발급**한 새 값을 위 시크릿에 넣으세요. 옛 값은 폐기합니다.

## 3. 웹 UI 로컬 개발 (`web/`)

```
cd web
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_SUPABASE_URL / ANON_KEY 채우기
npm run dev
```

Vercel에 배포할 때도 동일한 두 환경변수(`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`)를
Vercel 프로젝트 설정에 등록합니다.

## 4. 워커 로컬 테스트 (`worker/`)

```
cd worker
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
```

Supabase에 테스트 사용자 행을 만든 뒤(웹 UI로 로그인 후 설정 저장, 또는 SQL로 직접 insert),
환경변수를 설정하고 실행합니다:

```
python main.py --dry-run --force --user-id <테스트 user_id>
```

- `--dry-run`: 이메일 발송/이력 기록 없이 `output/` 폴더에 HTML만 저장
- `--force`: 발송 시각 창 체크를 건너뛰고 즉시 실행(테스트용)
- `--user-id`: 특정 사용자 1명만 처리

## 5. GitHub Actions 스케줄러

`.github/workflows/worker.yml`이 15분마다 워커를 실행하며, 매 실행마다 워커 스스로
"지금(±15분 창 안에서) 발송해야 할 사용자"를 사용자별 타임존 기준으로 판별합니다.
GitHub Actions 저장소 Settings → Secrets에 위 2번 표의 값을 모두 등록해야 합니다.

수동 테스트: Actions 탭 → `news-digest-worker` → Run workflow → `dry_run: true` 또는
`user_id`를 지정해 특정 사용자만 테스트할 수 있습니다.

## 알려진 제한사항 / 설계 결정

- Naver API 키, Gmail 발신 계정, OpenAI 키는 **서비스 전체가 공유**하는 자격증명입니다.
  사용자별로 다른 것은 키워드/발송시각/타임존/소스 토글/수신 이메일뿐입니다(각자 SMTP
  비밀번호를 입력받지 않아 노출·남용 위험을 줄임).
- GitHub Actions의 scheduled cron은 부하 시 지연될 수 있어 ±15~20분 오차를 허용합니다.
  `last_sent_date` 체크로 지연/재시도에도 중복 발송되지 않습니다.
- 크롤링 모듈(`worker/src/fetchers/crawler.py`)은 API가 없는 새 소스를 발굴하기보다, 기존
  Naver/Google 결과의 부실한 요약을 본문으로 보강하는 용도로 한정했습니다.
- 일일 LLM 비용 상한(`MAX_DAILY_LLM_COST_USD`, 기본 $0.5)을 넘으면 이후 호출은 전부
  원본 스니펫으로 자동 대체됩니다.
