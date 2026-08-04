# 데이터베이스 설계

## 1. 원칙

- 운영 기준은 PostgreSQL이며 식별자는 UUID 의미를 가진 `String(36)`, 시간은
  timezone-aware timestamp를 사용한다. 기존 schema 호환 migration이 끝난 뒤 PostgreSQL
  native UUID 전환 여부를 별도 결정한다.
- 사용자 확정 데이터, AI 원본, 실행 job을 분리한다.
- 실제 착용의 원장은 `wear_events`다.
- 삭제/기부/판매는 통계와 복구 요구를 고려해 lifecycle로 표현한다.
- schema 변경은 `create_all()`이 아니라 Alembic migration으로 관리한다.
- JSONB는 구조가 유동적인 결과에 사용하고, 검색·제약이 중요한 값은 컬럼으로 둔다.

## 2. Alembic baseline (`0001`)

```mermaid
erDiagram
    USERS ||--o{ AUTH_IDENTITIES : has
    USERS ||--o{ CLOSETS : owns
    CLOSETS ||--o{ ITEMS : contains
```

| 테이블 | baseline 역할 | 주요 한계 |
|---|---|---|
| `users` | email/nickname 계정 | profile/onboarding/settings 없음 |
| `auth_identities` | local identity와 password hash | OAuth/session 없음 |
| `closets` | 사용자 옷장 | default/archive 정책 없음 |
| `items` | 이미지 key와 분석/표시 값을 한 행에 저장 | AI 원본/파생 이미지/착용 lifecycle 분리 안 됨 |

`0001`은 이전 `Base.metadata.create_all()` 방식의 DB를 안전하게 stamp할 수 있도록 네
테이블 구조를 그대로 캡처한다.

## 3. ORM head 스키마 (`0002`)

```mermaid
erDiagram
    USERS ||--o{ AUTH_IDENTITIES : authenticates_with
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o| USER_PROFILES : has
    USERS ||--o| USER_PREFERENCES : configures
    USERS ||--o{ CLOSETS : owns
    USERS ||--o{ IMPORT_JOBS : requests
    USERS ||--o{ OUTFITS : receives
    USERS ||--o{ OUTFIT_FEEDBACK : reacts
    USERS ||--o{ WEAR_EVENTS : records
    USERS ||--o{ SUBSCRIPTIONS : subscribes

    CLOSETS ||--o{ ITEMS : contains
    CLOSETS ||--o{ IMPORT_JOBS : imports_into
    IMPORT_JOBS o|--o{ ITEMS : creates
    ITEMS ||--o{ ITEM_IMAGES : has
    ITEMS ||--o{ ANALYSIS_JOBS : requests
    ITEMS ||--o{ ITEM_ANALYSES : has_history
    ANALYSIS_JOBS ||--o| ITEM_ANALYSES : produces

    OUTFITS ||--|{ OUTFIT_ITEMS : consists_of
    ITEMS ||--o{ OUTFIT_ITEMS : included_in
    OUTFITS ||--o{ OUTFIT_FEEDBACK : receives
    OUTFITS ||--o{ WEAR_EVENTS : worn_as
    WEAR_EVENTS ||--o| OUTFIT_REVIEWS : reviewed_by
```

SQLAlchemy `Base.metadata`와 Alembic head는 위 17개 테이블을 구현하며 `alembic check`로
SQLite와 PostgreSQL 모두 schema diff가 없음을 검증한다.

## 4. 테이블 정의

### Identity와 Profile

#### `users`

- `id uuid PK`
- `email varchar(320) UNIQUE`
- `nickname varchar(80)`
- `status varchar(20)`
- `created_at`, `updated_at`, `deleted_at`

#### `auth_identities`

- `id uuid PK`, `user_id FK`
- `provider`: local/apple/google/kakao
- `subject`, `password_hash nullable`
- unique `(provider, subject)`

#### `refresh_tokens`

- `id uuid PK`, `user_id FK`
- `token_hash`, `device_id`
- `issued_at`, `expires_at`, `revoked_at`, `replaced_by_id`
- 원문 refresh token은 저장하지 않는다.

#### `user_profiles`

- `user_id PK/FK`
- `display_name`, `profile_image_key`
- `location_name`, `timezone`
- `gender_identity`, `height_cm`, `body_type`
- `personal_colors jsonb`
- `onboarding_completed_at`, `updated_at`

#### `user_preferences`

- `user_id PK/FK`
- `preferred_styles`, `disliked_styles`, `preferred_colors`
- `fit_preferences`, `ai_settings`, `notification_settings`
- `updated_at`

### Wardrobe와 Analysis

#### `closets`

- baseline 컬럼과 `is_default`, `archived_at`, `updated_at`
- partial unique index로 사용자별 default closet 하나를 보장한다.

#### `items`

- identity: `id`, `closet_id`
- 표시값: `display_name`, `brand`, `collection_name`
- 확정 분석값: `category`, `subcategory`, `materials`, `colors`, `style_tags`, `season_tags`
- 수집 정보: `source_type`, `purchase_price numeric`, `currency`, `acquired_at`
- 상태: `analysis_status`, `lifecycle_status`, `donated_at`
- cache: `last_worn_at`, `wear_count`
- audit: `created_at`, `updated_at`

`materials`와 `colors`를 JSONB로 시작할 수 있지만 검색 요구가 커지면 child table로
정규화한다.

- `analysis_status`: processing/ready/failed
- `lifecycle_status`: active/archived/donated/sold/discarded
- 기존 `status` 값은 `analysis_status` rename으로 보존한다.
- 기존 `image_key`는 `item_images` 전환이 끝날 때까지 compatibility bridge로 유지한다.

#### `item_images`

- `id`, `item_id`, `image_type`, `storage_key`
- `content_type`, `width`, `height`, `byte_size`, `sha256`
- `created_at`
- image type: original/mask/transparent/normalized/thumbnail

#### `analysis_jobs`

- `id`, `item_id`, `status`, `attempt`
- `provider`, `pipeline_version`, `error_code`
- `queued_at`, `started_at`, `completed_at`
- retry는 기존 행을 덮기보다 attempt를 추적한다.

#### `item_analyses`

- `id`, `item_id`, `analysis_job_id UNIQUE`
- `model_name`, `model_version`, `pipeline_version`
- `category`, `subcategory`, `materials`, `colors`
- `style_tags`, `season_tags`, `attributes`, `confidence`
- `raw_result`, `created_at`, `superseded_at`

#### `import_jobs`

- `id`, `user_id`, `closet_id`, `source_type`, `source_key`
- `status`, `detected_item_count`, `error_code`
- `created_at`, `completed_at`

### Outfit, Wear와 Analytics

#### `outfits`

- `id`, `user_id`, `source`, `status`
- `scheduled_for`, `occasion`
- `weather_snapshot`, `preference_snapshot`
- `overall_score`, `score_breakdown`
- `recommendation_reason`, `stylist_tip`, `scoring_version`
- `is_bookmarked`, `created_at`, `updated_at`

#### `outfit_items`

- `outfit_id`, `item_id`, `role`, `position`, `created_at`
- unique `(outfit_id, item_id)`

#### `outfit_feedback`

- `id`, `outfit_id`, `user_id`, `feedback_type`
- `reason_tags`, `created_at`, `updated_at`
- MVP에서는 unique `(user_id, outfit_id)`

#### `wear_events`

- `id`, `user_id`, `outfit_id`
- `worn_at`, `weather_snapshot`, `occasion`
- `idempotency_key`, `created_at`
- unique `(user_id, idempotency_key)`

#### `outfit_reviews`

- `id`, `wear_event_id UNIQUE`
- `rating` check 1~5
- `quick_tags`, `note`, `created_at`, `updated_at`

#### `subscriptions`

- `id`, `user_id`, `provider`, `external_subscription_id`
- `plan`, `status`, `current_period_end`, `cancel_at_period_end`
- unique `(provider, external_subscription_id)`

## 5. 인덱스

- `items(closet_id, created_at desc)`
- `items(closet_id, category, created_at desc)`
- 검색 방식 확정 후 normalized display name의 trigram 또는 full-text index
- `analysis_jobs(status, queued_at)`
- `outfits(user_id, scheduled_for desc)`
- `wear_events(user_id, worn_at desc)`
- `item_analyses(item_id, created_at desc)`

## 6. 삭제 정책

- User 탈퇴: 법적/운영 정책에 따라 개인 데이터 삭제 또는 익명화
- Item 제거: 기본은 `archived`; 명시적 영구 삭제는 image artifact와 파생 데이터 처리
- Closet 삭제: active item이 있으면 거부하거나 명시적 cascade 확인
- Outfit/Wear: 과거 analytics 보존 필요 시 item 표시 snapshot 또는 tombstone 사용
- Analysis raw result: 보존 기간을 두고 주기적으로 삭제 가능

## 7. Migration revision

1. `0001_baseline`: 기존 users/auth_identities/closets/items 캡처
2. `0002_expand_wireframe_domain_schema`:
   - profile/preferences/refresh session
   - item image/job/analysis/import
   - item analysis/lifecycle 상태 분리와 기존 데이터 default backfill
   - outfit/feedback/wear/review/subscription
   - owner/검색/집계 index와 check constraint
   - PostgreSQL 기존 JSON 컬럼을 JSONB로 변환

애플리케이션 시작 시 `RUN_DATABASE_MIGRATIONS=true`이면 versioned migration을 실행하며,
운영 배포에서는 별도 migration 단계 후 이 옵션을 끌 수 있다. `create_all()`은 더 이상
사용하지 않는다.

각 migration은 빈 DB와 기존 데이터 DB 모두에서 upgrade를 검증한다. 운영 데이터가 있는
컬럼은 nullable 추가 → backfill → constraint 강화 순서를 사용한다.
