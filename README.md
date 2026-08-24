# Cloth Vision API

사용자가 촬영한 의류 이미지를 분석해 디지털 옷장을 만들고, 색상·계절·스타일 기반의
기본 아이템 추천을 제공하는 FastAPI 백엔드입니다.

## 저장소 역할

이 프로젝트는 두 저장소로 구성됩니다.

- `cloth-vision`: HTTP API, 인증·인가, PostgreSQL, 이미지 저장, Core 조립
- `cloth-vision-core`: 이미지 전처리, 선택적 segmentation, OpenAI 멀티모달 분석,
  deterministic 아이템 매칭

로컬 개발에서는 API가 `../cloth-vision-core`를 editable dependency로 참조하므로 두
저장소를 반드시 같은 상위 디렉터리에 둡니다.

## 현재 구현 범위

- 이메일·비밀번호 회원가입/로그인과 JWT access token
- 사용자별 옷장 생성 및 최신 등록순 아이템 목록
- JPEG, PNG, WebP 의류 이미지 업로드와 로컬 파일 저장
- OpenAI Responses API 기반 의류 카테고리·색상 팔레트·소재·스타일·계절 분석
- 선택적 rembg segmentation과 mask/투명 이미지/분석용 crop 생성
- 분석 결과 조회와 사용자 보정
- 인증된 의류 이미지 조회
- 선택한 아이템과 다른 카테고리 아이템의 색상·계절·스타일 기반 추천
- 요청 method/path/status/duration/request ID access log

현재 업로드와 AI 분석은 한 HTTP 요청 안에서 동기 실행됩니다. 로컬 이미지는
`var/uploads/{item_id}/` 아래에 저장되며 운영용 object storage와 비동기 worker는 아직
연결되지 않았습니다.

## 사전 요구사항

- Git과 GitHub SSH 인증
- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/)
- Docker와 Docker Compose
- 멀티모달 분석을 사용할 경우 결제가 활성화된 OpenAI API key

두 GitHub 저장소가 비공개라면 `Just-Exit` organization에 대한 접근 권한도 필요합니다.

## 1. Clone

```bash
mkdir cloth
cd cloth

git clone git@github.com:Just-Exit/cloth-vision-api.git cloth-vision
git clone git@github.com:Just-Exit/cloth-vision-core.git cloth-vision-core
```

최종 디렉터리 구조는 다음과 같아야 합니다.

```text
cloth/
├── cloth-vision/
└── cloth-vision-core/
```

## 2. 환경변수 설정

```bash
cd cloth-vision
cp .env.example .env
```

`.env`에서 최소한 아래 값을 확인하거나 설정합니다.

```dotenv
APP_ENV=local
DATABASE_URL=postgresql+psycopg://cloth_vision:cloth_vision@localhost:5432/cloth_vision
RUN_DATABASE_MIGRATIONS=true

POSTGRES_DB=cloth_vision
POSTGRES_USER=cloth_vision
POSTGRES_PASSWORD=cloth_vision
POSTGRES_PORT=5432

UPLOAD_DIR=./var/uploads
MAX_UPLOAD_BYTES=10485760
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp

JWT_SECRET_KEY=replace-with-at-least-32-random-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=your-own-openai-api-key
OPENAI_VISION_MODEL=gpt-5.4-mini
OPENAI_OUTFIT_MODEL=gpt-5.4-mini

ENABLE_SEGMENTATION=false
SEGMENTATION_MODEL=u2netp

OPENWEATHER_API_KEY=your-openweathermap-api-key
WEATHER_LATITUDE=37.5665
WEATHER_LONGITUDE=126.9780
WEATHER_REFRESH_MINUTES=30
WEATHER_CACHE_MAX_AGE_MINUTES=90
```

로컬 JWT secret은 다음 명령으로 만들 수 있습니다.

```bash
openssl rand -hex 32
```

`.env`와 OpenAI API key는 커밋하거나 공유하지 않습니다. `OPENAI_API_KEY`가 비어 있거나
OpenAI 호출이 실패하면 아이템은 `failed` 상태가 되며 `analysis_warning`을 반환합니다.
segmentation mask가 없는 경우 Pillow가 배경을 의류 색상으로 추측하지 않고 색상도 빈
값으로 유지합니다.

segmentation을 함께 시험하려면 다음 값을 사용합니다.

```dotenv
ENABLE_SEGMENTATION=true
SEGMENTATION_MODEL=u2netp
```

rembg 모델은 처음 분석할 때 다운로드될 수 있어 첫 요청이 오래 걸릴 수 있습니다.

## 3. 의존성 설치

```bash
uv sync --all-extras
```

API 저장소의 가상환경에 API와 로컬 Core가 함께 editable installation 됩니다.

## 4. PostgreSQL 실행

```bash
docker compose up -d postgres
docker compose ps postgres
```

로그가 필요하면 다음 명령을 사용합니다.

```bash
docker compose logs -f postgres
```

DB schema는 서버 시작 시 Alembic head까지 자동 upgrade됩니다. 수동으로 실행하려면 다음
명령을 사용합니다.

```bash
uv run alembic upgrade head
uv run alembic check
```

## 5. API 서버 실행

로컬 PC에서만 테스트할 때:

```bash
uv run uvicorn cloth_vision_api.main:app --reload --port 8000
```

실제 모바일 기기에서 같은 네트워크를 통해 접근할 때:

```bash
uv run uvicorn cloth_vision_api.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000
```

Makefile을 사용해도 됩니다.

```bash
make db-up
make run
```

확인 주소:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

요청이 들어오면 터미널에 method, path, status, 처리 시간과 request ID가 기록됩니다.

```text
INFO [cloth_vision_api.access] POST /api/v1/auth/login status=200 duration_ms=184.2 request_id=req_...
```

## 6. API 빠른 테스트

아래 예시에서 `jq`를 사용하면 응답의 ID와 token을 편리하게 저장할 수 있습니다.

### 회원가입과 token 발급

```bash
ACCESS_TOKEN=$(
  curl -s -X POST 'http://127.0.0.1:8000/api/v1/auth/signup' \
    -H 'Content-Type: application/json' \
    -d '{
      "email": "tester@example.com",
      "password": "demo-password",
      "nickname": "tester"
    }' |
  jq -r '.access_token'
)
```

이미 가입한 계정은 로그인 endpoint를 사용합니다.

```bash
ACCESS_TOKEN=$(
  curl -s -X POST 'http://127.0.0.1:8000/api/v1/auth/login' \
    -H 'Content-Type: application/json' \
    -d '{
      "email": "tester@example.com",
      "password": "demo-password"
    }' |
  jq -r '.access_token'
)
```

### 옷장 생성

```bash
CLOSET_ID=$(
  curl -s -X POST 'http://127.0.0.1:8000/api/v1/closets' \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"name":"테스트 옷장"}' |
  jq -r '.id'
)
```

기존 옷장 목록은 다음 API로 확인합니다.

```bash
curl 'http://127.0.0.1:8000/api/v1/closets' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 의류 이미지 업로드와 분석

업로드는 `multipart/form-data`이며 `display_name`은 받지 않습니다. 자동 분석은 상품명이나
소재를 추정하지 않고 카테고리·색상·계절·스타일과 시각 속성을 반환합니다. 표시명은
`상의`, `하의`, `아우터`, `신발`, `액세서리` 같은 일반명을 사용하며 필요하면 사용자가
상세 수정 API로 직접 변경할 수 있습니다.

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/items" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'image=@/absolute/path/to/garment.jpg'
```

카테고리를 알고 있다면 힌트를 선택적으로 전달할 수 있습니다.

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/items" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'category=outer' \
  -F 'image=@/absolute/path/to/jacket.jpg'
```

허용 category는 `top`, `bottom`, `outer`, `shoes`, `accessory`, `unknown`입니다. AI 분류를
확인하려면 category를 생략합니다.

다음과 같은 응답은 provider 분석이 실패하고 로컬 분석으로 fallback했다는 뜻입니다.

```json
{
  "category": "unknown",
  "confidence": 0,
  "user_attributes": {
    "analysis_warning": "vision_provider_failed"
  }
}
```

OpenAI에서 `429 insufficient_quota`가 발생하면 API Billing과 project usage limit을
확인합니다.

### 최신순 옷장 아이템 목록

```bash
curl \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/items" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

응답은 최신 등록순 배열이며 각 아이템에 인증 이미지 경로가 포함됩니다.

```json
[
  {
    "id": "item-uuid",
    "display_name": "상의",
    "image_url": "/api/v1/items/item-uuid/image",
    "images": {
      "original_url": "/api/v1/items/item-uuid/images/original",
      "transparent_url": "/api/v1/items/item-uuid/images/transparent",
      "normalized_url": "/api/v1/items/item-uuid/images/normalized",
      "thumbnail_url": "/api/v1/items/item-uuid/images/thumbnail"
    },
    "created_at": "2026-08-21T01:55:32Z"
  }
]
```

### 아이템 이미지 조회

```bash
ITEM_ID='item-uuid'

curl \
  "http://127.0.0.1:8000/api/v1/items/$ITEM_ID/image" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --output item-image.jpg
```

옷장 목록에서는 `images.thumbnail_url`, 분석 상세 화면에서는 `images.normalized_url`을
사용합니다. segmentation이 비활성화됐거나 기존 아이템에 파생 이미지가 없으면 서버가
원본으로 fallback합니다. 모바일 이미지 컴포넌트도 이미지 요청에 같은 Bearer token을
전달해야 합니다.

### 아이템 상세와 추천

```bash
curl \
  "http://127.0.0.1:8000/api/v1/items/$ITEM_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

```bash
curl \
  "http://127.0.0.1:8000/api/v1/items/$ITEM_ID/recommendations?limit=5" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

추천 API는 선택한 아이템과 다른 category이며 `ready` 상태인 같은 옷장 아이템만 색상,
계절, 스타일 기준으로 비교합니다. 후보가 없으면 빈 배열을 반환합니다.

### 옷장 전체 코디 추천

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/outfit-recommendations" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"limit":3}'
```

이 API는 특정 아이템을 기준으로 하지 않고 옷장의 모든 `ready` 아이템으로 코디를
구성합니다. 상의와 하의는 필수이며, 등록돼 있다면 아우터·신발·액세서리를 단계적으로
추가합니다. 상의×하의 조합을 계산한 뒤 각 단계에서 상위 20개 후보만 유지하고 최종적으로
다양한 상의가 포함된 최대 3개의 코디를 반환합니다. 조합마다 LLM을 호출하지 않고 최종
후보에만 LLM이 짧은 `reason`과 `stylist_tip`을 작성합니다. LLM 호출이 실패하거나 키가
없으면 같은 필드를 규칙 기반 문구로 반환합니다.

각 결과의 `image_url`은 추천 의류를 한 장에 배치한 WebP 이미지입니다. segmentation
산출물이 있으면 배경이 제거된 이미지를 우선 사용하며, 없으면 원본을 사용합니다. 이 URL도
Bearer 토큰이 필요합니다. 예:
`GET /api/v1/closets/{closet_id}/outfit-recommendations/{outfit_id}/image`.

필수 카테고리가 부족하면 `outfits`는 빈 배열이며 `missing_categories`에 필요한 카테고리가
포함됩니다.

### 옷장 분석

```bash
curl \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/analytics" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

선택한 옷장의 `ready` 의류를 기준으로 `color_distribution`, `season_balance`,
`category_distribution`, `essential_recommendations`를 반환합니다. 각 분포의 `ratio`는
`0~1` 범위입니다. 착용 기록 없이는 알 수 없는 많이 입은 컬러, 안 입는 옷, 착용당 비용은
응답에 포함하지 않습니다. 필수 아이템은 현재 없는 카테고리를 우선순위대로 최대 3개
반환하며, 모든 핵심 카테고리가 있으면 빈 배열입니다.

### 홈 대시보드

```bash
curl \
  "http://127.0.0.1:8000/api/v1/closets/$CLOSET_ID/dashboard" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

앱 홈 화면에서 필요한 `nickname`, 시간대별 `greeting`, `today_outfit`,
`closet_summary`, `stylist_tip`, 최근 등록순 `recent_items` 최대 5개를 한 번에 반환합니다.
`closet_summary.completeness_score`는 상의·하의·아우터·신발·액세서리 5개 핵심
카테고리 중 보유한 카테고리 비율입니다. 상의와 하의가 모두 있어야 `today_outfit`이
생성되며, 부족하면 `null`을 반환합니다. `OPENWEATHER_API_KEY`가 설정되면 서버가 서울
현재 날씨를 시작 시점부터 30분 간격으로 PostgreSQL의 `weather_cache` 테이블에 갱신하고
`weather`에 반환합니다. 날씨 호출 실패 시 DB의 마지막 캐시를 유지하며 90분 이상 지난
값은 `is_stale=true`입니다. 여러 API worker와 서버 재시작 후에도 같은 캐시를 사용합니다.
온도에 맞는 계절 태그를 오늘의 코디 정렬에 반영합니다. 키가 없으면 `weather=null`이며,
착용 기록이 필요한 이번 달 착용 수는 포함하지 않습니다.

## 7. 테스트와 정적 검사

API 테스트:

```bash
uv run pytest
uv run ruff check src tests
```

Core 테스트:

```bash
cd ../cloth-vision-core
PYTHONPATH=src ../cloth-vision/.venv/bin/python -m pytest -q
../cloth-vision/.venv/bin/ruff check src tests
```

API 전체 검증은 다음 명령으로 실행할 수 있습니다.

```bash
cd ../cloth-vision
make check
```

## 8. 종료와 데이터 초기화

PostgreSQL 컨테이너 종료:

```bash
docker compose down
```

DB volume까지 삭제해 완전히 초기화:

```bash
docker compose down -v
```

`down -v`는 모든 로컬 DB 데이터를 삭제합니다. 업로드 이미지는 별도
`var/uploads/`에 있으므로 필요하면 명시적으로 정리해야 합니다.

## 문서

- [`API_LIST.md`](API_LIST.md): 화면 요구사항 기준 API 진행 상태
- [`ROADMAP.md`](ROADMAP.md): 우선순위와 구현 순서
- [`WIREFRAME_BACKEND_GAP_ANALYSIS.md`](WIREFRAME_BACKEND_GAP_ANALYSIS.md): 화면별 API·DB gap
- [`guide/`](guide/): 아키텍처, 도메인, DB, API, AI pipeline, 보안과 테스트 설계
