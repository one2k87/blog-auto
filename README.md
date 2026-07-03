# AdSense 카테고리 집중 수익형 블로그 생성기 (한국어)

여러 **고단가 카테고리**(예: 금융/재테크 · 건강/생활 · 경제/IT)를 각각 미니사이트처럼 운영하며,
**카테고리마다 매일 같은 형식(6슬롯)** 으로 글을 생성합니다. 카테고리별로 히스토리·내부링크가
독립적으로 쌓여 각각의 클러스터가 됩니다. 각 카테고리 안에서:

- **저경쟁 롱테일 4슬롯**: 시리즈 2 + 단일 2 (경쟁 약해 상위노출 쉬운 좁은 주제)
- **시즌 선점 2슬롯**: 시리즈 1 + 단일 1 (앞으로 검색 붙을 시기를 2~4주 선점)
- **시리즈**는 하나의 주제를 2~3편으로 이어 쓰고 편끼리 내부링크+루프(마지막→처음)로 묶습니다.
  **시리즈는 1슬롯으로 카운트**(3편이어도 1건). 즉 하루 6슬롯 = 실제 글은 더 많이 생성.
- 매일 **이전 글로 내부링크**를 걸어 카테고리 클러스터를 쌓아 **반복 수익** 구조를 만듭니다.

각 글은 애드센스 실전 전략 5가지를 조건으로 반영합니다: **3초 후킹 첫문장 · 이미지→그 아래 문단 사이
광고 자리+유도문장 · 고단가 키워드 배치(제목/첫문단/중반/끝) · 요약표·이미지로 체류시간 · 내부링크**.
글에 쓰이는 **이미지는 AI로 전부 자동 생성**되고, 매 실행마다 후보 주제를 **저경쟁/시즌으로 지속 판별**합니다.

```
히스토리(중복방지)  ─▶  카테고리 주제 생성(저경쟁+시즌)  ─▶  수익형 글(내부링크)  ─▶  WP 게시/복붙
   │                        │                                    │
발행 이력 축적          네이버 실측 검색량                    대시보드 + 구글시트
```

---

## 1. 폴더 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 파이프라인 (이것만 실행). 카테고리·히스토리·내부링크 관리 |
| `topics.py` | 카테고리 안에서 저경쟁/시즌 주제를 중복없이 생성 |
| `generator.py` | 수익형 글(HTML) 생성: 후킹·광고자리·요약표·내부링크·FAQ |
| `metrics.py` | 네이버 검색광고 실측 검색량·경쟁도·꾸준함 |
| `images.py` | 글 이미지 AI 자동 생성 (Gemini/OpenAI) |
| `llm.py` | OpenAI / Anthropic / Gemini 통합 호출 |
| `links.py` | 주제별 **실제** 참고 링크 검색 (DuckDuckGo) |
| `publisher.py` | WordPress REST API 자동 게시 |
| `sheets.py` | 구글시트 로깅 |
| `dashboard/data/history.json` | 발행 이력(중복 방지 + 내부링크 자산) |
| `dashboard/index.html` | 결과 확인·복붙용 웹/아이폰 대시보드 |
| `config.example.json` | 설정 예시 (복사해서 `config.json` 으로) |

---

## 2. 설치 (5분)

```bash
cd adsense-blog-automation
python3 -m venv venv && source venv/bin/activate   # 선택
pip install -r requirements.txt
cp config.example.json config.json                  # 설정 파일 생성
```

`requirements.txt` 의 LLM 패키지는 **본인이 쓸 것 하나만** 설치해도 됩니다
(예: OpenAI만 쓰면 `openai`만 있으면 됨).

---

## 3. 설정 (`config.json`)

### (1) LLM — 글을 쓰는 두뇌 (필수)
셋 중 하나를 고르고 API 키만 넣으면 됩니다. 비용이 가장 저렴한 추천 조합:

| provider | model 예시 | 비고 |
|---|---|---|
| `openai` | `gpt-4o-mini` | 가성비 좋음 (추천) |
| `anthropic` | `claude-3-5-sonnet-20241022` | 글 품질 우수 |
| `gemini` | `gemini-1.5-flash` | 무료 한도 넉넉 |

```json
"llm": { "provider": "openai", "api_key": "sk-...", "model": "gpt-4o-mini" }
```

### (2) WordPress — 자동 게시 (선택)
1. 워드프레스 관리자 → **사용자 → 프로필** 하단의 **응용 프로그램 비밀번호** 발급
2. 발급된 비밀번호(공백 포함)를 그대로 입력

```json
"wordpress": {
  "enabled": true,            // false 면 게시 안 하고 복붙용 HTML만 저장
  "site_url": "https://내블로그.com",
  "username": "워드프레스ID",
  "app_password": "abcd efgh ijkl mnop qrst uvwx",
  "status": "draft"           // draft=검토후발행(안전), publish=즉시발행
}
```
> 처음에는 `"status": "draft"` 로 두고 글 품질을 확인한 뒤 `publish` 로 바꾸는 걸 권장합니다.
> AdSense 정책상 자동 생성 글을 무검수로 대량 발행하면 위험할 수 있어요(아래 7번 참고).

### (3) 구글시트 로깅 (선택)
1. Google Cloud에서 **서비스 계정** 생성 → JSON 키 다운로드 → `service_account.json` 으로 저장
2. **Google Sheets API** 사용 설정
3. 기록할 시트를 만들고, 서비스 계정 이메일(`...@...iam.gserviceaccount.com`)을 **편집자로 공유**
4. 시트 URL의 `/d/` 와 `/edit` 사이 ID를 `spreadsheet_id` 에 입력

```json
"sheets": { "enabled": true, "service_account_file": "service_account.json",
            "spreadsheet_id": "1AbC...XyZ" }
```

---

## 4. 실행

```bash
python main.py
```
- WordPress `enabled:true` → 자동 게시 (draft 또는 publish)
- `enabled:false` → `output/` 폴더에 **복붙용 HTML** 저장
- 두 경우 모두 `dashboard/data/latest.json` 생성 → 대시보드에 표시

---

## 5. 매일 아침 7시 자동 실행

### macOS / Linux (cron)
```bash
chmod +x run_daily.sh
crontab -e
# 아래 한 줄 추가 (매일 07:00). 경로는 본인 절대경로로.
0 7 * * * /절대경로/adsense-blog-automation/run_daily.sh
```

### Windows (작업 스케줄러)
1. 작업 스케줄러 → 기본 작업 만들기 → 매일 07:00
2. 동작: 프로그램 시작 → `python` / 인수 `main.py` / 시작 위치는 프로젝트 폴더

> Cowork에서 이 대화에 "매일 아침 7시에 실행해줘"라고 요청하면 예약 작업으로도 등록할 수 있습니다.

---

## 6. 대시보드 사용

`dashboard/index.html` 을 엽니다. 두 가지 방법:

- **간단(권장):** 프로젝트 폴더에서 `python -m http.server 8000` 실행 후
  브라우저에서 `http://localhost:8000/dashboard/` 접속 → `latest.json` 자동 표시
- **그냥 더블클릭:** 파일을 바로 열면 보안상 JSON 자동로드가 막힐 수 있어요.
  이때는 상단 **📂 JSON 불러오기** 버튼으로 `dashboard/data/latest.json` 을 직접 선택

대시보드 기능: 높은/낮은 경쟁력·언어별 필터, **HTML 복사 / 텍스트 복사 / 제목 복사**,
미리보기, 참고 링크, 게시 상태 확인.

---

## 6.5 SEO 최적화 (자동 적용)

생성되는 모든 글에는 검색 노출을 높이는 요소가 자동으로 들어갑니다:

- **포커스 키워드 배치**: 제목 앞부분 · 첫 문단(첫 100단어) · H2 소제목 · 메타설명에 자연스럽게 1회씩
- **제목 50~60자 / 메타설명 120~155자**: 검색 스니펫이 잘리지 않는 길이
- **SEO 슬러그(URL)**: 영문 소문자-하이픈으로 자동 생성(예: `epson-l3150-driver-windows11`) → 워드프레스 글 주소에 반영
- **제목 구조 + 목차**: H1 1개 + H2/H3 계층, H2가 3개 이상이면 앵커 목차(TOC) 자동 삽입
- **가독성**: 짧은 문단, 리스트, 핵심 구절 강조 → 체류시간↑ (애드센스에 유리)
- **외부 신뢰 링크**: 주제 검색으로 찾은 실제 권위 링크 1~2개 삽입(가짜 URL 방지)
- **이미지 alt 텍스트** 제안값 포함
- **FAQ 섹션 + 구조화 데이터(JSON-LD)**: `BlogPosting` + `FAQPage` 스키마를 글에 자동 삽입 → 구글이
  '자주 묻는 질문' 리치 결과로 노출할 수 있음 (PAA 공략)

> 워드프레스에 Yoast/Rank Math 같은 SEO 플러그인이 있다면, 위 슬러그·메타가 그대로 채워져 더 잘 맞물립니다.
> 더 강한 효과를 원하면 글 발행 후 대표 이미지 1장(alt 텍스트 활용)과 내부 링크 1~2개를 직접 추가하세요.

---

## 6.6 실측 검색량으로 키워드 선별 (수치 기반)

`config.json`의 `metrics.provider`를 설정하면, 후보 키워드를 넉넉히 모은 뒤 **실제 검색량 수치**로
높은/낮은 경쟁력을 선별합니다. 대시보드·구글시트에 월검색량·경쟁도·꾸준함이 함께 표시됩니다.

- **높은 경쟁력** = 실측 월검색량이 **가장 많은** 상위 5개
- **낮은 경쟁력** = 월검색량이 `low_volume_floor`~`low_volume_ceil`(기본 100~8,000) 사이면서
  **꾸준함(상록성)이 높은** 상위 5개

세 가지 데이터 소스 중 선택:

| provider | 무엇을 재나 | 정확도 | 설정 난이도 | 비고 |
|---|---|---|---|---|
| `naver` | 네이버 월간 검색수(PC+모바일) | 정확(절대값) | 쉬움·무료 | **한국 블로그 추천** |
| `google_ads` | 구글 월평균 검색수 | 정확(절대값) | 어려움 | 개발자토큰 승인+OAuth 필요 |
| `trends` | Google Trends 관심도(0~100) | 상대값 | 매우 쉬움·무료 | 절대 검색량 아님 |
| `none` | 측정 안 함 | — | — | 트렌드/LLM 판단만 |

> **꾸준함(상록성)** 점수는 provider와 무관하게 Google Trends 최근 12개월 변동으로 계산합니다
> (`use_trends_steadiness: true`). 1(100%)에 가까울수록 계절·유행 없이 매달 일정하게 검색됨을 뜻합니다.

### 네이버 검색광고 API 발급 (권장)
1. https://searchad.naver.com 가입(사업자 아니어도 개인 가입 가능).
2. 우측 상단 **도구 → API 사용 관리 → API 라이선스 발급**.
3. 얻는 값 3가지를 `config.json`(또는 GitHub 시크릿)에 입력:
   - **액세스 라이선스** → `api_key` (`NAVER_API_KEY`)
   - **비밀키** → `secret_key` (`NAVER_SECRET_KEY`)
   - **고객 ID**(내 계정 번호) → `customer_id` (`NAVER_CUSTOMER_ID`)
4. `metrics.provider`를 `naver`로 설정. (클라우드면 시크릿 `METRICS_PROVIDER=naver`)

### Google Ads 키워드플래너 (구글 실측이 꼭 필요할 때)
`pip install google-ads` 후, 개발자 토큰·OAuth(client_id/secret/refresh_token)·`login_customer_id`를
`metrics.google_ads`에 입력하고 `provider`를 `google_ads`로. (개발자 토큰은 신청·승인이 필요해 시간이 걸립니다.)

### 가장 쉬운 시작: trends
아무 키 없이 `provider`를 `trends`로 두면 됩니다. 절대 검색량 대신 **관심도(0~100)**로 순위를 매기고
꾸준함도 함께 계산합니다. 정확한 숫자가 필요하면 나중에 `naver`로 올리세요.

---

## 6.7 카테고리 집중 & 주제를 계속 뽑아내는 원리 (핵심 전략)

이 도구는 참고 자료의 5가지 전략을 코드로 옮긴 것입니다.

### 왜 카테고리 집중인가
- 한 카테고리에 글이 쌓이면(예: 금융 30개) 방문자가 **한 글 → 내부링크 → 다음 글**로 연달아 읽어
  체류시간·재방문·수익이 함께 올라갑니다(미니사이트).
- 고단가 카테고리(금융/보험/건강/기술)에 집중하면 같은 클릭이라도 **광고 단가**가 높습니다.

### 주제를 '계속' 뽑는 방법 (중복 없이 무한 생성)
1. `config.json`의 `site.category` / `category_desc`가 **주제의 울타리**입니다. 이 안에서만 뽑습니다.
2. 매일 두 갈래로 생성합니다.
   - **저경쟁 롱테일(`long`)**: 좁고 명확한 주제(예: "무직자 소액 비상금 대출 조건"). 네이버 실측으로
     검색량이 `low_volume_floor~ceil`(기본 100~8,000)이고 경쟁이 낮은 것을 우선 채택 → 상위노출 쉬움.
   - **시즌 선점(`season`)**: 다음 달에 검색이 붙을 주제를 지금 미리(2~4주 선점). 월별 시즌 힌트를 자동 반영.
3. **중복 방지**: 지금까지 발행한 제목/키워드를 `dashboard/data/history.json`에 쌓아,
   다음 생성 때 "이미 다룬 주제"로 프롬프트에 넣습니다. → 매일 새로운 각도의 주제가 나옵니다.
4. **내부링크 자동**: 새 글마다 같은 카테고리의 최근 글 2~3개로 "함께 보면 좋은 글"을 연결 → 클러스터가 커집니다.

### 카테고리 추가·변경 (여러 개 운영)
`config.json`의 `categories` 배열에 원하는 만큼 카테고리를 넣으면, **각 카테고리마다** 아래 `counts`
(6슬롯)로 동일하게 생성됩니다. 카테고리별로 히스토리·내부링크가 분리됩니다.
```json
"blog_url": "https://내블로그.com",
"categories": [
  { "name": "금융/재테크", "desc": "대출, 카드, 정부지원금, 연금, 세금 등 고단가 금융 주제" },
  { "name": "건강/생활",   "desc": "다이어트, 영양제, 탈모, 수면 등 건강·생활 주제" },
  { "name": "경제/IT",     "desc": "물가·금리 경제, AI 도구, 앱 사용법 등 경제/IT 주제" }
]
```
예: 카테고리 3개면 하루 3×6 = 18슬롯(시리즈 포함 시 실제 글은 더 많음). 클라우드에선 시크릿
`CATEGORIES_JSON`에 위 배열을 그대로 넣으면 됩니다(미입력 시 이 3개가 기본).

### 수익형 글 구조(자동 적용)
3초 후킹 첫문장(질문/공감) · 목차 · 요약표 · **이미지 → 그 아래 광고 자리 + 정책 안전한 유도문장**
· 제목/첫문단/중반/끝 키워드 배치 · 내부링크 · FAQ + JSON-LD. 광고 자리에는 애드센스 코드만 붙이면 됩니다.

### 시리즈 글 (2~3편 묶음)
`counts`의 `long_series`, `season_series`가 시리즈 슬롯 수입니다. 시리즈는 한 주제를
`series_min_parts`~`series_max_parts`(기본 2~3)편으로 나눠 각 편을 완성 글로 쓰고,
편끼리 "📚 시리즈 N편" 내비게이션 + 마지막→처음 루프로 묶어 재방문·체류시간을 높입니다.
**대시보드·히스토리에서 시리즈는 1건으로 계산**되지만 실제 글은 편 수만큼 생성됩니다.

### 이미지 자동 생성 (글당 1개)
`images.provider`로 **글마다 대표 이미지 1개**를 AI가 자동 생성합니다(본문 상단, 그 아래 광고 자리).
- `gemini`(기본): LLM의 Gemini 키를 재사용(Imagen). 키에 이미지 모델 권한이 있어야 함.
- `openai`: `gpt-image-1`. `images.api_key`에 OpenAI 키 입력.
- `none`: 이미지 대신 '자리 표시'만.
게시(WordPress) 시 이미지는 미디어로 업로드해 URL로 삽입, 복붙 모드에서는 본문에 인라인(base64)으로 들어갑니다.
> 이미지 생성은 별도 과금이 될 수 있습니다. 무료로 쓰려면 `none`으로 두거나, 생성 실패 시 자동으로 자리 표시로 대체됩니다.

### 저경쟁/시즌 지속 판별
매 실행마다 후보 주제를 LLM으로 **저경쟁(long)** 인지 **시즌(season)** 인지 분류하고,
저경쟁은 네이버 실측 검색량(밴드+낮은 경쟁)으로 한 번 더 걸러 각 슬롯에 배치합니다.
판별 근거는 대시보드/시트에 함께 남습니다.

> 클라우드(GitHub Actions) 시크릿: `CATEGORY`, `CATEGORY_DESC`, `BLOG_URL`, `COUNT_LONG`, `COUNT_SEASON`,
> `INSERT_ADS`, `METRICS_PROVIDER=naver`, `NAVER_*` 로 위 설정을 그대로 넣을 수 있습니다.

---

## 7. AdSense 운영 시 주의 (중요)

구글은 **자동 생성된 저품질 대량 콘텐츠**를 정책 위반으로 봅니다. 안전하게 쓰려면:
- 처음엔 `status: draft` 로 두고 **사람이 검수 후 발행**
- 하루 10개를 전부 그대로 쓰기보다 **사실 확인·가독성 보완** 후 게시
- 참고 링크와 수치는 반드시 한 번 검증 (LLM이 틀릴 수 있음)
- 낮은 경쟁력(상록성) 글이 경쟁이 약하고 꾸준히 검색돼 신생 블로그의 노출·수익에 유리합니다

---

## 8. 문제 해결

| 증상 | 해결 |
|---|---|
| Trends RSS 403 / 빈 결과 | 자동으로 LLM이 키워드를 대신 생성합니다. `trends_geo` 를 `US` 등으로 바꿔도 됨 |
| 글에 링크가 안 들어감 | `pip install ddgs` 확인. 검색 실패 시 링크 없이 글만 생성 |
| WordPress 401/403 | 응용 프로그램 비밀번호·아이디 확인, 사이트가 REST API 허용하는지 확인 |
| 시트 기록 안 됨 | 서비스 계정 이메일을 시트에 **편집자 공유**했는지 확인 |

---

## 9. 📱 아이폰 앱으로 설치하기 (모바일)

대시보드는 **PWA**라서 아이폰 홈 화면에 추가하면 진짜 앱처럼 전체화면으로 열립니다.
단, **아이폰은 파이썬을 직접 못 돌리므로** 글 생성·게시(매일 7시)는 **클라우드에서 자동 실행**하고,
아이폰 앱은 그 결과를 보고 **탭 한 번으로 워드프레스에 게시**하는 역할을 합니다.

```
[GitHub Actions · 매일 07시]  글 생성 → data/latest.json 저장
              │
       [GitHub Pages]  로 공개
              │
   [아이폰 홈화면 앱(PWA)]  결과 확인 · 복사 · 워드프레스 게시
```

### 9-1. 클라우드 자동화 켜기 (GitHub Actions, 무료)
1. 이 폴더를 GitHub 저장소로 올립니다(`git init && git add . && git commit && git push`).
2. 저장소 **Settings → Secrets and variables → Actions** 에서 시크릿 등록:
   - `LLM_PROVIDER` (예: `openai`), `LLM_API_KEY`, `LLM_MODEL` (예: `gpt-4o-mini`)
   - `LANGS` = `ko,en`
   - (자동 게시 원하면) `WP_ENABLED`=`true`, `WP_SITE`, `WP_USER`, `WP_APP_PASSWORD`, `WP_STATUS`=`draft`
3. `.github/workflows/daily-blog.yml` 이 **매일 07:00 KST**(UTC 22:00)에 자동 실행됩니다.
   - 탭 **Actions → 매일 블로그 자동 생성 → Run workflow** 로 지금 바로 테스트도 가능.
4. 실행되면 `dashboard/data/latest.json` 이 저장소에 자동 커밋됩니다.

### 9-2. 대시보드를 웹에 공개 (GitHub Pages)
1. 저장소 **Settings → Pages → Source: Deploy from a branch → main / (root)** 저장.
2. 잠시 후 주소가 생깁니다: `https://<아이디>.github.io/<저장소>/dashboard/`
3. 데이터 파일 주소: `https://<아이디>.github.io/<저장소>/dashboard/data/latest.json`

### 9-3. 아이폰에 설치
1. 사파리(Safari)로 위 `.../dashboard/` 주소 접속.
2. 하단 **공유 버튼(□↑) → 홈 화면에 추가**.
3. 홈 화면 아이콘으로 열면 전체화면 앱으로 실행됩니다.
4. 앱 안 **⚙️ 설정**에서:
   - **데이터 주소**에 9-2의 `latest.json` 주소 입력 → 매일 새 글 자동 표시
   - **폰에서 실행(GitHub)**: owner/repo/토큰 입력 → 상단 **▶ 버튼**으로 "지금 생성 실행"(수동 트리거)
   - **워드프레스 정보** 입력 → 글마다 **📤 게시** 버튼으로 폰에서 바로 발행
   > ▶ 실행용 토큰은 GitHub Fine-grained PAT(해당 저장소 Actions: Read/Write). 상세 가이드 PART 8 참고.

> 안드로이드도 크롬에서 "홈 화면에 추가"로 동일하게 설치됩니다.

### 9-4. 폰에서 게시할 때 CORS 설정 (필요 시)
폰의 앱(다른 도메인)에서 워드프레스로 직접 게시하면 브라우저 CORS에 막힐 수 있습니다.
이때 워드프레스에 아래 코드를 **mu-plugin**(`wp-content/mu-plugins/cors.php`)으로 추가하세요.
`https://<아이디>.github.io` 를 본인 PWA 주소로 바꾸면 됩니다.

```php
<?php
add_action('rest_api_init', function () {
  remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');
  add_filter('rest_pre_serve_request', function ($value) {
    $origin = 'https://<아이디>.github.io';   // ← 본인 PWA 도메인
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Headers: Authorization, Content-Type');
    return $value;
  });
}, 15);
```
> CORS 설정이 번거로우면, 게시는 클라우드 자동화(9-1, `WP_ENABLED=true`)에 맡기고
> 아이폰 앱은 **확인·복사·검수 용도**로만 써도 됩니다. 이게 가장 간단합니다.

---

## 부록. 어떤 운영 방식이 좋을까
| 방식 | 자동 게시 | 7시 자동 | 폰 사용 | 난이도 |
|---|---|---|---|---|
| A. 내 PC에서 cron + 복붙 | ✗(복붙) | ✓ | △ | 쉬움 |
| B. 클라우드(Actions) 자동 게시 + 폰은 확인만 | ✓ | ✓ | ✓ | 보통 (추천) |
| C. 클라우드 생성 + 폰에서 직접 게시 | ✓(폰) | ✓ | ✓ | 보통(+CORS) |
```
