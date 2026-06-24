# AdSense 자동 블로그 생성기

매일 아침 자동으로 **핫이슈 키워드 5개 + 세분화(롱테일) 주제 5개 = 하루 10개**의 블로그 글을
한국어·영어로 생성하고, WordPress에 자동 게시(또는 복붙용으로 저장)한 뒤
웹 대시보드와 구글시트로 관리하는 도구입니다.

```
키워드 수집  ─▶  글 생성(한/영 + 참고링크)  ─▶  WordPress 게시 or 복붙 HTML
   │                                                │
Google Trends RSS                              웹 대시보드 + 구글시트 로그
```

---

## 1. 폴더 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 파이프라인 (이것만 실행) |
| `trends.py` | Google Trends 인기검색어 수집 + 세분화 주제 프롬프트 |
| `generator.py` | LLM으로 블로그 글(HTML) 생성 |
| `llm.py` | OpenAI / Anthropic / Gemini 통합 호출 |
| `links.py` | 주제별 **실제** 참고 링크 검색 (DuckDuckGo) |
| `publisher.py` | WordPress REST API 자동 게시 |
| `sheets.py` | 구글시트 로깅 |
| `dashboard/index.html` | 결과 확인·복붙용 웹 대시보드 |
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

대시보드 기능: 핫이슈/세분화·언어별 필터, **HTML 복사 / 텍스트 복사 / 제목 복사**,
미리보기, 참고 링크, 게시 상태 확인.

---

## 7. AdSense 운영 시 주의 (중요)

구글은 **자동 생성된 저품질 대량 콘텐츠**를 정책 위반으로 봅니다. 안전하게 쓰려면:
- 처음엔 `status: draft` 로 두고 **사람이 검수 후 발행**
- 하루 10개를 전부 그대로 쓰기보다 **사실 확인·가독성 보완** 후 게시
- 참고 링크와 수치는 반드시 한 번 검증 (LLM이 틀릴 수 있음)
- 세분화(롱테일) 글이 보통 경쟁이 약해 노출·수익에 유리합니다

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
   - **워드프레스 정보**(사이트·아이디·앱비밀번호·게시방식) 입력 → 글마다 **📤 게시** 버튼으로 폰에서 바로 발행

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
