# ORBIT — Backend

사립학교 교직원의 **노후 준비 진단 · 연금 시뮬레이션** 서비스 ORBIT의 백엔드 모노레포입니다.

Spring Boot(회원/인증/결과 저장)와 FastAPI(연금·자산 계산 엔진)를 Nginx 리버스 프록시 뒤에 두고,
Docker Compose로 함께 구동합니다.

<br>

## 목차

- [아키텍처](#아키텍처)
- [기술 스택](#기술-스택)
- [디렉토리 구조](#디렉토리-구조)
- [빠르게 실행하기](#빠르게-실행하기)
- [환경 변수](#환경-변수)
- [API 개요](#api-개요)
- [계산 엔진](#계산-엔진)
- [백테스트 검증](#백테스트-검증)
- [테스트](#테스트)
- [배포](#배포)
- [컨벤션](#컨벤션)

<br>

## 아키텍처

```
                        ┌──────────────────────────┐
   Browser (Vercel)     │        nginx :80         │
        ────────────►   │                          │
                        │  /api/  ──► spring :8080 │
                        │  /ai/   ──► fastapi :8000│
                        └────────┬─────────┬───────┘
                                 │         │
                     ┌───────────▼───┐ ┌───▼──────────────┐
                     │  Spring Boot  │ │     FastAPI      │
                     │  회원/인증    │ │  연금 계산 엔진  │
                     │  결과 저장    │ │  (stateless)     │
                     └───────┬───────┘ └───┬──────────────┘
                             │             │
                       ┌─────▼─────┐  ┌────▼─────────────┐
                       │ MySQL 8.0 │  │ active_income_   │
                       │  (JPA)    │  │ stats.csv (RO)   │
                       └───────────┘  └──────────────────┘
```

**역할 분리 원칙**

- **FastAPI** — 순수 계산 서버. DB도 세션도 없고, 요청 값만으로 결과를 만들어 돌려줍니다.
- **Spring** — 회원/인증과 "계산 결과 원본 보관"을 담당합니다. 저장 시 **재계산하지 않고**
  프론트가 받은 응답 body를 JSON 그대로 보존합니다(`diagnoses.result_json`).
  대신 `status` / `depletion_age`만 목록 조회용으로 추출·검증합니다.
- **nginx** — `/api/`는 Spring, `/ai/`는 FastAPI로 라우팅합니다.
  FastAPI는 `root_path="/ai"`로 떠 있어 Swagger 문서 경로도 프록시 뒤에서 정상 동작합니다.

<br>

## 기술 스택

| 영역 | 스택 |
|:--|:--|
| API 서버 | Spring Boot 4.0.6 · Java 17 · Spring Data JPA · springdoc-openapi 3.0.3 |
| 계산 서버 | FastAPI 0.115 · Python 3.13 · Pydantic v2 · pandas |
| DB | MySQL 8.0 (운영) / H2 (Spring 테스트) |
| 인프라 | Docker Compose · nginx · AWS EC2 |
| CI/CD | GitHub Actions (테스트 → 이미지 빌드 → EC2 배포) |

<br>

## 디렉토리 구조

```
BE/
├── spring/                      # Spring Boot — 회원/인증/진단 결과 저장
│   ├── src/main/java/com/orbit/
│   │   ├── users/               # 회원가입·로그인·토큰 재발급·회원정보
│   │   ├── diagnoses/           # 계산 결과 원본 저장/조회
│   │   └── global/              # 인증 주입, CORS, OpenAPI, 전역 예외 처리
│   ├── src/main/resources/      # application(.local/.prod).yml
│   └── db/migrations/           # 수동 SQL 마이그레이션
│
├── fastapi/                     # FastAPI — 연금/자산 계산 엔진
│   ├── app/
│   │   ├── routers/             # /api/employees, /api/retirement
│   │   ├── schemas/             # 요청/응답 스키마 + 금액 단위 변환(money.py)
│   │   ├── services/            # 계산 로직 · 법령 규칙 모듈
│   │   └── repositories/        # 소득 통계 CSV 로딩
│   ├── data/                    # 소득 통계 원본/전처리 데이터
│   ├── scripts/                 # EDA · 전처리 스크립트
│   ├── backtest/                # 계산엔진 검증 파이프라인 (분석 전용)
│   │   ├── scripts/  reports/  analysis/  config/
│   └── tests/                   # 단위 + 골든 스냅샷 테스트
│
├── nginx/default.conf
├── compose.yaml                 # 운영: mysql + spring + fastapi + nginx
├── compose.local.yaml           # 로컬: mysql만 (앱은 IDE에서 실행)
└── .env.example
```

<br>

## 빠르게 실행하기

### 사전 준비

```bash
cp .env.example .env
```

### 1) 전체 스택 (Docker)

```bash
docker compose --env-file .env up -d --build
```

| 대상 | URL |
|:--|:--|
| 헬스체크 | http://localhost/ |
| Spring Swagger | http://localhost/api/docs |
| FastAPI Swagger | http://localhost/ai/docs |

### 2) 로컬 개발 (DB만 컨테이너)

DB만 띄우고 두 앱은 IDE/터미널에서 직접 실행합니다. 로컬 MySQL은 **3307** 포트로 매핑됩니다.

```bash
# DB
docker compose -f compose.local.yaml --env-file .env up -d

# FastAPI  (http://localhost:8000)
cd fastapi
pip install -r requirements.txt
uvicorn app.main:app --reload

# Spring   (http://localhost:8080)
cd spring
./gradlew bootRun          # 기본 프로파일: local
```

> FastAPI는 기동 시 `data/active_income_stats.csv`의 존재와 필수 컬럼(`구간`, `평균`)을 검증합니다.
> 파일이 없으면 `scripts/preprocess.py`로 생성하세요.

<br>

## 환경 변수

`.env.example`를 복사해 사용합니다. **`.env`는 커밋하지 않습니다.**

| 변수 | 설명 | 기본값 |
|:--|:--|:--|
| `SPRING_PROFILES_ACTIVE` | Spring 프로파일 | `local` |
| `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_ROOT_PASSWORD` | MySQL 계정 | — |
| `DB_HOST` / `DB_PORT` | 로컬 실행 시 DB 접속 정보 | `localhost` / `3307` |
| `AUTH_TOKEN_SECRET` | 토큰 서명 시크릿 **(운영 필수)** | 로컬 전용 기본값 존재 |
| `AUTH_ACCESS_TOKEN_VALIDITY_SECONDS` | 액세스 토큰 만료 | `3600` (1시간) |
| `AUTH_REFRESH_TOKEN_VALIDITY_SECONDS` | 리프레시 토큰 만료 | `1209600` (14일) |
| `FASTAPI_BASE_URL` | Spring이 참조하는 FastAPI 주소 | `http://localhost:8000` |
| `FASTAPI_DATA_DIR` | FastAPI 데이터 볼륨 경로 (읽기 전용 마운트) | `./fastapi/data` |
| `CORS_ALLOWED_ORIGINS` | 허용 Origin (콤마 구분, **Spring/FastAPI 공통**) | `http://localhost:5173` |

> `AUTH_TOKEN_SECRET`은 compose에서 필수 값으로 강제되어, 미설정 시 컨테이너가 뜨지 않습니다.
> 운영 값은 파일이 아니라 EC2 systemd `Environment=` 또는 GitHub Secrets로 주입합니다.

<br>

## API 개요

### Spring — `/api` (Swagger: `/api/docs`)

인증은 `Authorization: Bearer <accessToken>` 헤더를 사용하며,
컨트롤러는 `@AuthenticatedUser User` 파라미터로 인증 사용자를 주입받습니다.

| Method | Path | 설명 | 인증 |
|:--|:--|:--|:--:|
| POST | `/api/users/signup` | 회원가입 | |
| POST | `/api/users/login` | 로그인 (access + refresh 발급) | |
| POST | `/api/auth/refresh` | 토큰 재발급 | |
| GET | `/api/users/me` | 내 정보 조회 | ✔ |
| PATCH | `/api/users/me` | 내 정보 수정 (자산·월지출·근속연수·월연금·월급 등) | ✔ |
| POST | `/api/users/logout` | 로그아웃 (액세스/리프레시 토큰 즉시 무효화) | ✔ |
| DELETE | `/api/users/me` | 회원 탈퇴 (보유 진단 기록 함께 삭제) | ✔ |
| GET | `/api/diagnoses` | 저장한 모든 진단 요약 목록 (최신순) | ✔ |
| GET | `/api/diagnoses/{id}` | 진단 상세 (종류 무관, 원본 그대로) | ✔ |
| POST/GET | `/api/diagnoses/retirement/diagnosis` | 은퇴자산 진단 결과 저장/조회 | ✔ |
| POST/GET | `/api/diagnoses/retirement/reduction` | 재취업 감액 결과 저장/조회 | ✔ |
| POST/GET | `/api/diagnoses/retirement/recommendations` | 개선 추천 결과 저장/조회 | ✔ |
| POST/GET | `/api/diagnoses/employees/simulate` | 재직자 연금 시뮬레이션 결과 저장/조회 | ✔ |
| POST/GET | `/api/diagnoses/employees/scenarios` | 수령방식 시나리오 결과 저장/조회 | ✔ |

**토큰** — 외부 JWT 라이브러리 없이 `HmacSHA256` 기반 자체 서명 토큰을 사용하며,
액세스/리프레시 토큰 모두 평문이 아니라 **SHA-256 해시**로 DB에 저장되어, 로그아웃 시 즉시 무효화됩니다.

### FastAPI — `/ai` (Swagger: `/ai/docs`)

| Method | Path | 설명 |
|:--|:--|:--|
| POST | `/api/retirement/diagnosis` | 은퇴 자산 진단 — 고갈 시점 · 준비 상태 · 연도별 timeline |
| POST | `/api/retirement/recommendations` | 100세까지 무고갈(`SUFFICIENT`) 도달에 필요한 최소 절약액/추가소득액 |
| POST | `/api/retirement/reduction` | 재취업 소득에 따른 연금 감액 (2025년 소득심사 기준 고정) |
| POST | `/api/employees/simulate` | 재직자 예상 연금월액 · 일시금 · 퇴직수당 |
| POST | `/api/employees/scenarios` | 정상/조기/일시금/분할 4개 수령방식 비교 및 최적안 |
| GET | `/health` | 헬스체크 |

**금액 단위 규약** — API 경계는 전부 **원(₩) 단위 정수**, 내부 계산은 **만원 단위**입니다.
변환은 `app/schemas/money.py`의 `WonAmountInput` / `WonAmountOutput` 타입 별칭이
Pydantic 직렬화 시점에 전담하며, 서비스 코드에서는 별도 곱셈/나눗셈을 하지 않습니다.

**에러 응답** — 두 서버 모두 동일한 형태로 통일되어 있습니다.

```json
{
  "code": "VALIDATION_ERROR",
  "message": "입력값이 올바르지 않습니다.",
  "details": [{ "field": "current_age", "reason": "1 이상이어야 합니다." }],
  "timestamp": "2026-09-04T00:00:00Z"
}
```

<br>

## 계산 엔진

`fastapi/app/services/`의 각 모듈은 **법령 근거와 데이터 근거를 분리해** 관리합니다.
법령이 확정한 값은 상수로 고정하고, 데이터로 추정한 값은 그 사실을 docstring에 명시합니다.

### 지급률 모형 — 법정 tranche + α (`pension_rate_model.py`)

```
연금월액 = 기준소득월액 × Σ( 연도별 법정 지급률 × 해당 구간 개월수 / 12 )
```

- 지급률은 단일 상수가 아니라 **연도별 tranche**입니다.
  2009년 이전 2.0% · 2010~2015년 1.9% · 2016년부터 매년 인하되어 2035년 이후 1.70% 고정.
- 2009년 이전 구간의 법정 산정기초(평균보수월액)를 우리는 보유하지 않아
  평균기준소득월액으로 대체합니다. 이 대체로 생기는 체계적 격차를 흡수하는
  **단일 스칼라 α = 0.5311**만 데이터로 추정했습니다.
- **파라미터가 1개**이므로 2009년 이전 재직기간이 없는 미래 퇴직자에게는
  α가 아예 곱해지지 않고 법정 요율만 적용됩니다 — 구조적으로 외삽 가능합니다.

### 재직기간 상한 (`service_cap_rules.py`)

사학연금법 부칙(법률 제13561호) **제11조 경과조치**를 그대로 구현합니다.
2016.1.1 시점 인정 재직월수에 따라 33/34/35/36년을 차등 적용하고,
적용 근거를 `cap_basis`(`STATUTORY_TIERED` / `STATUTORY_DEFAULT` / `DEFAULT_MAX`)로 응답에 노출합니다.

> 퇴직수당 상한(33년)은 **별개 조문**이므로 `employees_service.SEVERANCE_YEARS_CAP`에
> 따로 분리되어 있습니다. 값이 우연히 같아도 통합하지 않습니다.

### 재취업 감액 (`reduction_rules.py`)

국민연금 소득심사 기준을 연도별 `ReductionRule`로 테이블화했습니다(2023~2025).
새 연도의 A값이 공지되면 **코드 수정 없이 목록에 항목만 추가**하면 됩니다.
감액은 노령연금액의 1/2을 넘지 못합니다(`MAX_REDUCTION_RATIO = 0.5`).

### 자산 시뮬레이션 (`retirement_service.py`)

| 가정 | 값 |
|:--|:--|
| 자산 운용 수익률 | 3% |
| 물가상승률(지출 증가율) | 2% |
| 연금 증가율 | 0% |
| 목표연령 | 남 84세 / 여 88세 (통계청 생명표 60세 기대여명) |
| 시뮬레이션 상한 | 100세 |
| 절약 상한 | 월 생활비의 30% |
| 조기수령 감액 | 미달연수 1년당 5% (연 단위 올림, 평생 적용) |

판정 결과는 `SUFFICIENT`(고갈 없음) / `MIDDLE`(목표연령 이후 고갈) / `INSUFFICIENT`(목표연령 이전 고갈)입니다.

<br>

## 백테스트 검증

`fastapi/backtest/`는 **프로덕션 코드가 아니라 계산엔진 검증 파이프라인**입니다.
사학연금공단 제공 퇴직급여 마이크로데이터(n=40,719)로 지급률 모형을 5-fold 교차검증했습니다.

| 모형 | 적중률(전체) | 적중률(닫힌구간) | ±1구간 |
|:--|--:|--:|--:|
| baseline (0.017 단일 상수) | 43.54% | 19.99% | 92.94% |
| 법정 tranche (α 없음) | 37.63% | 11.49% | 84.44% |
| **tranche + α (채택)** | **68.99%** | **65.64%** | **98.08%** |

핵심 관찰은 **법정 요율을 보정 없이 그대로 쓰면 baseline보다 나빠진다**는 점입니다
(법정 요율이 전부 0.017보다 높아 기존의 과대추정 편향이 악화). α 도입 후
미적중 방향이 과대 98%/과소 2% → 과대 56%/과소 44%로 균형에 가까워졌습니다.

한때 적중률 80.39%를 낸 **30-파라미터 모형은 의도적으로 철회**했습니다.
과거 퇴직자 표본의 재직기간 구성을 통째로 학습해 미래 퇴직자에게 체계적으로
과소추정할 위험이 있었기 때문입니다. 전체 경위는 `backtest/analysis/README.md`에 보존되어 있습니다.

**주요 문서**

| 파일 | 내용 |
|:--|:--|
| `backtest/reports/final_report_tranche_alpha.md` | 최종 요약 (3모형 비교, α 추정) |
| `backtest/reports/scope_limitations.md` | 검증 범위와 한계 (개방구간·상한절단 등) |
| `backtest/reports/engine_defects.md` | 백테스트로 발견한 엔진 결함 |
| `backtest/reports/three_model_comparison.md` | 세그먼트별 전체 비교표 |
| `backtest/analysis/README.md` | 철회된 30-파라미터 모형 기록 |

> ⚠️ **데이터 취급 제한** — 원자료는 제공기관 공지에 따라 학교명 삭제, 금액은 구간값만 사용,
> 프로젝트 목적 외 사용·외부 노출이 금지됩니다. 모든 리포트에는 원본 금액 수치가 없습니다.

<br>

## 테스트

```bash
# FastAPI — 148 케이스
cd fastapi && pytest -q

# Spring
cd spring && ./gradlew test
```

- **골든 스냅샷 테스트** — `fastapi/tests/golden/`의 14개 JSON이 응답 계약을 고정합니다.
  계산 결과가 의도치 않게 바뀌면 즉시 실패하며, 의도된 변경 시에는 `_generate.py`로 갱신합니다.
- 그 외 금액 단위 정합성, 에러 응답 포맷, CORS 설정, 데이터 기동 검증, 법령 규칙 단위 테스트를 포함합니다.
- Spring 테스트는 H2 인메모리 DB로 인증 플로우와 진단 저장/조회 계약을 검증합니다.

<br>

## 배포

`main` 브랜치 push 시 `.github/workflows/deploy.yml`이 동작합니다.

```
Spring 테스트 → FastAPI 테스트 → 두 이미지 빌드 → EC2 SSH 배포 (compose up -d)
```

필요한 GitHub Secrets: `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, `EC2_APP_DIR`.

<br>

## 컨벤션

**브랜치** — `feature/{이슈번호}-{설명}`, `fix/...`, `refactor/...` → `develop` → `main`

**커밋** — 이모지 + 타입 + 한국어 요약

```
✨ Feat:      새로운 기능
🐛 Fix:       버그 수정
♻️ Refactor:  리팩토링
🧪 Test:      테스트
📊 Chore:     분석·문서·설정
⏪ Revert:    되돌리기
```

이슈/PR은 `.github/` 아래 템플릿을 따릅니다.

<br>

---

<div align="center">

**ORBIT** · 사립학교 교직원 노후 준비 진단 서비스 · Capstone Project

</div>
