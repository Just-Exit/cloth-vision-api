# HTTP API 계약

## 1. 공통 규칙

- Base URL: `/api/v1`
- Content-Type: JSON, 이미지 업로드만 `multipart/form-data`
- 인증: `Authorization: Bearer <access_token>`
- 날짜/시간: ISO 8601, timezone offset 또는 `Z` 포함
- ID: UUID
- enum: 영문 `snake_case`
- 클라이언트에 표시할 한국어 문구와 안정적인 오류 코드를 분리한다.

공개 endpoint:

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/oauth/{provider}/exchange`
- `POST /auth/refresh`

그 외 endpoint는 인증이 필요하다.

## 2. 오류 형식

```json
{
  "detail": "사용자에게 표시 가능한 설명",
  "code": "ITEM_ANALYSIS_FAILED",
  "request_id": "req_...",
  "fields": {}
}
```

| Status | 의미 |
|---:|---|
| 400 | 형식은 맞지만 수행할 수 없는 요청 |
| 401 | 인증 없음/만료/실패 |
| 403 | 인증됐지만 권한 없음 |
| 404 | 리소스가 없거나 소유하지 않음 |
| 409 | 중복/상태 충돌 |
| 413 | 업로드 크기 초과 |
| 415 | 지원하지 않는 파일 형식 |
| 422 | 필드 또는 이미지 검증 실패 |
| 429 | rate limit |
| 503 | 일시적 외부 provider 장애 |

소유하지 않은 리소스는 존재 여부 노출을 줄이기 위해 404를 사용할 수 있다.

## 3. 현재 구현 API

| Method | Path | 상태 |
|---|---|---|
| GET | `/health` | 구현 |
| POST | `/auth/signup` | 구현 |
| POST | `/auth/login` | 구현 |
| GET | `/auth/me` | 구현 |
| POST | `/closets` | 구현 |
| GET | `/closets` | 구현 |
| POST | `/closets/{closet_id}/items` | 동기 분석으로 구현 |
| GET | `/closets/{closet_id}/items` | filter/pagination 없이 구현 |
| GET | `/items/{item_id}` | 구현, image URL 없음 |
| PATCH | `/items/{item_id}` | 일부 분석 필드만 구현 |
| DELETE | `/items/{item_id}` | hard delete로 구현 |
| GET | `/items/{item_id}/recommendations` | pairwise 추천으로 구현 |

현재 API 동작의 정확한 schema는 실행 중인 `/docs`를 기준으로 한다.

## 4. 목표 API

### 인증

| Method | Path | 목적 |
|---|---|---|
| POST | `/auth/oauth/{provider}/exchange` | Apple/Google/Kakao code/token 교환 |
| POST | `/auth/refresh` | refresh rotation |
| POST | `/auth/logout` | 현재 session revoke |

OAuth exchange는 provider, subject, 검증된 email과 nonce를 서버에서 검증한다. provider
token을 단순 decode한 클라이언트 값을 신뢰하지 않는다.

### 프로필과 설정

| Method | Path | 목적 |
|---|---|---|
| GET | `/profile` | 프로필과 온보딩 상태 |
| PATCH | `/profile` | 이름·지역·체형 등 수정 |
| POST | `/profile/image` | 프로필 이미지 업로드 |
| PUT | `/profile/onboarding/body` | 체형 프로필 단계 upsert |
| GET | `/preferences` | 취향/AI 설정 |
| PATCH | `/preferences` | 설정 수정 |
| GET | `/subscription` | plan과 entitlement |

### 옷장과 분석

| Method | Path | 목적 |
|---|---|---|
| POST | `/closets/{closet_id}/items` | item과 analysis job 생성 |
| GET | `/closets/{closet_id}/items` | 검색 가능한 목록 |
| GET | `/items/{item_id}` | 이미지와 확정 분석 상세 |
| PATCH | `/items/{item_id}` | 사용자 보정 |
| DELETE | `/items/{item_id}` | archive 또는 정책에 따른 삭제 |
| POST | `/items/{item_id}/reanalyze` | 새 분석 attempt |
| GET | `/items/{item_id}/analyses` | 분석 이력 |
| GET | `/analysis-jobs/{job_id}` | job 상태/오류 |
| POST | `/items/bulk-lifecycle` | 기부 등 일괄 상태 변경 |
| POST | `/import-jobs` | screenshot/OOTD import |
| GET | `/import-jobs/{job_id}` | import 상태와 생성 item |

목록 예시:

```http
GET /api/v1/closets/{closet_id}/items?category=outer&q=blazer&sort=recent&limit=30
```

```json
{
  "items": [],
  "next_cursor": null,
  "total_count": 42
}
```

허용 query:

- `category`: top/bottom/outer/shoes/accessory
- `q`: 이름·브랜드 검색
- `sort`: recent/oldest/name
- `status`: active/processing/failed 등
- `cursor`, `limit`

업로드 성공은 장시간 분석 결과가 아니라 job을 반환한다.

```json
{
  "item_id": "uuid",
  "analysis_job_id": "uuid",
  "status": "queued"
}
```

### 코디, 착용과 리뷰

| Method | Path | 목적 |
|---|---|---|
| POST | `/outfit-recommendations` | context 기반 outfit 생성 |
| GET | `/outfits/{outfit_id}` | outfit 상세 |
| PUT | `/outfits/{outfit_id}/bookmark` | 저장 상태 설정 |
| POST | `/outfits/{outfit_id}/feedback` | like/dislike upsert |
| POST | `/outfits/{outfit_id}/wear` | wear event 생성 |
| GET | `/wear-events/{wear_event_id}` | 리뷰 화면 데이터 |
| PUT | `/wear-events/{wear_event_id}/review` | review upsert |

추천 요청 예시:

```json
{
  "date": "2026-08-04",
  "occasion": "office_meeting",
  "closet_id": "uuid",
  "excluded_item_ids": []
}
```

추천 응답은 `outfit_id`, 역할별 items, context, `overall_score`, `score_breakdown`, reasons,
stylist tip을 포함한다.

착용 생성에는 `Idempotency-Key` 헤더를 사용한다.

### 홈과 분석

| Method | Path | 목적 |
|---|---|---|
| GET | `/dashboard?date=YYYY-MM-DD` | 홈 composite response |
| GET | `/analytics/wardrobe?period=6m` | 옷장 분석 카드 |
| GET | `/analytics/wardrobe/report` | 전체 리포트 |

dashboard 응답 영역:

- `profile_summary`
- `weather`
- `recommended_outfit`
- `wardrobe_score`
- `monthly_worn_item_count`
- `stylist_tip`
- `recent_items`

## 5. 이미지 접근

DB의 `storage_key`를 공개 계약으로 직접 반환하지 않는다.

선택지:

1. 인증 endpoint: `GET /items/{item_id}/images/{image_id}`
2. 짧은 만료 시간의 signed URL

목록에는 thumbnail, 상세에는 normalized/original 접근 권한을 목적에 맞게 제공한다. URL은
만료될 수 있으므로 영속 식별자로 사용하지 않는다.

## 6. Versioning과 호환성

- `/api/v1` 안에서는 필드 추가를 우선한다.
- enum 추가 시 오래된 클라이언트 fallback을 고려한다.
- 필드 삭제/의미 변경은 새 API version 또는 명시된 deprecation 기간을 사용한다.
- OpenAPI contract test와 모바일 mock fixture를 함께 갱신한다.
