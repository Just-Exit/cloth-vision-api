# 테스트 전략

## 1. 목표

테스트는 endpoint 존재 여부가 아니라 다음 사용자 흐름의 신뢰성을 보장한다.

```text
로그인
→ 체형 프로필
→ 의류 업로드/분석
→ 분석 보정과 옷장 조회
→ 코디 추천
→ 오늘 입기와 리뷰
→ dashboard/analytics 반영
```

## 2. 테스트 계층

```text
많음   Domain/Core unit tests
       Application service tests
       Repository/provider contract tests
       API integration tests
적음   PostgreSQL + worker integration tests
최소   Mobile-to-backend end-to-end tests
```

단위 테스트만 SQLite로 통과한 것을 운영 DB 검증으로 간주하지 않는다.

## 3. 현재 테스트 상태

현재 `tests/test_api.py`는 다음을 검증한다.

- health
- 이메일 signup/login과 인증 누락
- closet 생성
- item 이미지 업로드와 대표색
- item 목록과 일부 수정
- 잘못된 MIME 거부

누락된 주요 영역:

- PostgreSQL repository
- 다른 사용자 리소스 접근
- item detail/delete/recommendation의 전체 경계값
- profile/onboarding
- 비동기 analysis job
- outfit/wear/review/dashboard/analytics
- OAuth, refresh token, image access

## 4. Domain/Core 단위 테스트

### 이미지와 분석

- EXIF orientation
- 손상/저해상도/과대 pixel 이미지
- mask가 없는 경우와 잘못된 mask
- palette 비율/HEX/LAB validation
- provider의 unknown enum, NaN confidence, 과도한 tag
- 사용자 보정이 AI 원본을 변경하지 않음

### 추천

- 동일 입력과 scoring version은 동일 결과
- score는 0~100
- weight 합과 rounding
- hard constraint 위반 없음
- donated/failed item 제외
- 날씨/occasion/profile 없음 fallback
- `too_hot`/`too_cold` feedback 반영
- 최근 outfit 반복 제한

### Analytics

- 월/계절/timezone 경계
- 0회 착용과 가격 없음
- 기부/보관 item 포함 정책
- wear event 중복 방지
- cost per wear 계산

## 5. Application 테스트

각 use case는 fake repository/storage/provider로 검증한다.

- transaction 성공/rollback
- 소유권 거부
- upload 저장 실패 시 orphan cleanup
- provider timeout/retry 분류
- analysis 성공 시 결과 저장과 item projection
- 재분석이 사용자 확정값을 덮지 않음
- wear idempotency key
- review upsert와 rating/tag validation
- subscription webhook 중복 처리

## 6. Repository Contract

모든 repository 구현에 같은 contract suite를 적용한다.

- add/get/list/save/delete 또는 lifecycle transition
- unique와 FK constraint
- transaction rollback
- UTC timestamp round trip
- JSONB field round trip
- cursor 정렬 안정성
- owner-scoped query
- concurrent update 정책

SQLite suite와 별도로 PostgreSQL container에서 실행한다.

## 7. API Integration

### 인증

- signup/login/me
- 중복 email과 잘못된 password
- 만료/위조 access token
- refresh rotation/reuse/logout
- OAuth issuer/audience/nonce 실패

### 프로필

- 체형 값 round trip
- 키 범위와 enum 오류
- 부분 수정 시 다른 필드 보존
- 다른 사용자 profile 접근 차단

### 의류와 이미지

- 정상 upload → 202/job ID
- queued/running/succeeded/failed 조회
- category/search/sort/cursor 조합
- total count와 thumbnail URL
- signed URL 만료 또는 인증 image 접근
- 다른 사용자 closet/item/image 접근 차단
- archive/donate 후 추천 제외

### Outfit와 Review

- 다중 item과 role 반환
- weather/occasion context 보존
- bookmark idempotency
- like ↔ dislike upsert
- wear 중복 탭 방지
- rating 1/5 경계와 0/6 거부
- 허용되지 않은 quick tag 거부

### Dashboard와 Analytics

- 빈 옷장/빈 착용 기록
- 오늘 outfit 있음/없음
- weather provider 실패 fallback
- 사용자 timezone 기준 월 집계
- review 저장 후 값 반영

## 8. AI Golden Fixture

fixture에는 라이선스와 기대값을 함께 관리한다.

필수 범주:

- top/bottom/outer/shoes/accessory
- 단색/무채색/다색/패턴
- 복잡한 배경, 사람 착용, 바닥 촬영
- blur/저조도/과노출/crop
- 여러 아이템과 의류 없음

fixture metadata:

- expected validation
- expected category 후보
- reference mask 또는 bounding box
- reference palette/LAB 허용 범위
- 데이터 출처와 사용 허가

모델/provider 변경 전후에 accuracy, schema failure, latency와 cost를 비교한다.

## 9. 외부 Provider와 장애 테스트

mock/fake는 다음을 재현해야 한다.

- 정상 응답
- timeout
- 429와 retry-after
- 5xx
- 잘못된 JSON/schema
- 느린 응답
- 중복 webhook
- 만료/잘못된 OAuth token

retry 횟수와 최종 user-safe error code를 검증한다.

## 10. 비기능 테스트

- 목록/dashboard p95 latency
- 동시 upload와 job queue 처리
- 대용량/decompression bomb 방어
- object storage 일시 장애
- DB migration upgrade와 기존 데이터 backfill
- backup/restore rehearsal
- 로그 secret/PII redaction
- dependency vulnerability scan

## 11. CI 단계

권장 순서:

```text
format check
→ lint/type check
→ unit tests
→ API tests with SQLite
→ PostgreSQL repository tests
→ migration check
→ Core integration tests
→ artifact build
```

AI golden evaluation과 부하 시험은 비용/시간에 따라 nightly 또는 release gate로 분리한다.

## 12. 완료 기준

기능 완료는 다음을 모두 만족한다.

- 요구사항 ID와 테스트가 연결됨
- 정상·권한·validation·provider 실패 경로 포함
- migration과 PostgreSQL 검증
- OpenAPI contract 갱신
- 로그에 token/이미지/리뷰 노트가 없음
- 관련 Core/API 양쪽 테스트 통과
- 화면의 loading/empty/error 상태를 재현할 fixture 존재
