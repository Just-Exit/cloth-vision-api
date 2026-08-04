# 보안과 개인정보 설계

## 1. 보호 대상

- 비밀번호 hash, access/refresh token, OAuth credential
- 이메일과 provider identity
- 체형, 키, personal colors와 취향
- 위치/지역과 날씨 context
- 원본 의류/착용 이미지와 EXIF
- outfit, wear history, rating과 자유 입력 노트
- 결제 subscription identifier와 entitlement

체형·위치·착용 기록은 사용자 개인 특성을 추론할 수 있으므로 일반 옷장 데이터보다
보수적으로 취급한다.

## 2. 인증

### Local login

- 비밀번호는 Argon2id로 hash한다.
- 가입/로그인 오류가 계정 존재 여부를 과도하게 노출하지 않게 한다.
- 로그인 endpoint에 IP/account 기준 rate limit을 적용한다.
- 비밀번호 재설정 도입 시 단회성·짧은 만료 token을 사용한다.

### Social OAuth

- Apple/Google/Kakao 공식 flow와 server-side 검증을 사용한다.
- issuer, audience, signature, expiry, nonce/state를 검증한다.
- 클라이언트가 전달한 email/profile을 검증 없이 신뢰하지 않는다.
- 같은 email이라는 이유만으로 계정을 자동 병합하지 않는다.
- provider subject를 identity의 안정적 식별자로 사용한다.

### Token/session

- access token은 짧은 만료 시간을 사용한다.
- refresh token은 rotation하고 DB에는 hash만 저장한다.
- 재사용이 감지된 token family를 revoke한다.
- logout은 현재 device/session을 명확히 revoke한다.
- JWT secret과 provider secret은 환경별 secret store에서 관리한다.

## 3. 인가와 소유권

모든 사용자 리소스는 ID 조회 뒤 소유권을 검사한다.

- closet → `user_id`
- item → closet → `user_id`
- outfit/wear/review → `user_id`
- analysis/import job → item/요청 사용자
- image → item/profile 소유자

목록 query에도 소유자 조건을 첫 조건으로 포함한다. UUID를 안다고 다른 사용자 리소스에
접근할 수 없어야 한다. 존재 여부 노출을 줄이기 위해 비소유 리소스는 404로 응답할 수 있다.

## 4. 이미지 업로드와 제공

### 업로드

- request body byte limit
- 실제 image decode와 MIME/확장자 교차 검증
- 최대 pixel count, 최소 해상도와 frame 수 제한
- 파일명을 storage path로 직접 사용하지 않음
- 임의 storage key와 path traversal 방지
- decoder/provider는 제한된 권한과 자원에서 실행
- EXIF orientation 적용 후 GPS 등 metadata 제거 정책

### 저장과 조회

- 원본과 파생 이미지는 private bucket/storage에 둔다.
- object key를 공개 식별자로 사용하지 않는다.
- 짧은 signed URL 또는 인증 image endpoint를 사용한다.
- thumbnail과 원본 권한을 목적에 맞게 분리할 수 있다.
- 삭제 시 original/mask/thumbnail 등 모든 artifact를 추적한다.

## 5. 개인정보 최소화

| 데이터 | 목적 | 최소화 원칙 |
|---|---|---|
| 키/체형 | 실루엣·핏 추천 | 실제 추천에 쓰지 않으면 수집하지 않음 |
| 위치 | 날씨 추천 | 정밀 좌표 대신 도시/일시 조회 후 미보존 고려 |
| personal colors | 추천 개인화 | 진단/선호 의미를 사용자에게 명확히 표시 |
| 리뷰 노트 | 개인화 | 자유 입력을 로그/analytics payload에 복제하지 않음 |
| 이미지 | 의류 분석 | 얼굴/배경이 필요 없으면 파생본에서 제거 |

수집 목적, 보존 기간, 계정 탈퇴 시 처리와 third-party provider 전송 사실을 개인정보
처리방침에 반영한다.

## 6. 외부 Provider

### AI/Vision/LLM

- 이미지 또는 분석 facts가 어떤 provider에 전송되는지 설정으로 추적한다.
- provider의 data retention/training opt-out 정책을 확인한다.
- API key와 request 원문을 로그에 남기지 않는다.
- LLM에는 점수 계산에 필요한 최소 facts만 보내고 불필요한 사용자 식별자를 제거한다.

### Weather

- 정밀 위치 저장을 최소화한다.
- provider URL/query가 로그에 좌표를 노출하지 않게 한다.

### Payment webhook

- signature와 timestamp 허용 범위를 검증한다.
- provider event ID를 unique하게 저장해 replay를 막는다.
- 클라이언트가 주장하는 구매 상태만으로 entitlement를 부여하지 않는다.

## 7. 로그와 관측성

기록 가능:

- request ID, route, status, latency
- 내부 user ID의 제한된 형태
- job ID, provider 이름, error code, attempt
- 파일 byte size, dimension, validation 결과

기록 금지:

- Authorization/Cookie header
- access/refresh token과 OAuth code
- 비밀번호와 hash
- 이미지 bytes/signed URL
- provider secret
- 리뷰 노트 원문
- 불필요한 email/정밀 위치

## 8. 데이터 삭제와 보존

- item hard delete 시 DB 행과 모든 image artifact의 처리 결과를 확인한다.
- 계정 탈퇴는 session revoke 후 profile/images/reviews/subscription projection을 정책대로
  삭제 또는 익명화한다.
- 분석 raw result와 provider payload는 최소 보존 기간을 설정한다.
- backup에서의 삭제 반영 기간을 정책에 명시한다.
- 삭제 job 실패를 재시도하고 운영자가 확인할 수 있게 한다.

## 9. 위협 점검표

| 위협 | 통제 |
|---|---|
| IDOR | repository query의 owner scope와 API 테스트 |
| credential stuffing | rate limit, 모니터링, 안전한 오류 |
| refresh token 탈취 | hash, rotation, reuse detection |
| 악성 이미지/decompression bomb | byte/pixel limit, decoder isolation |
| path traversal | 서버 생성 storage key와 resolved path 검증 |
| signed URL 유출 | 짧은 만료, private bucket, 로그 제거 |
| OAuth token 위조 | issuer/audience/signature/nonce 검증 |
| webhook replay | signature, timestamp, unique event ID |
| prompt injection | 구조화 schema, tool/secret 접근 금지, 출력 검증 |
| 과도한 개인정보 수집 | 목적 제한과 보존 정책 |

## 10. 출시 전 필수 점검

- [ ] 개발 기본 JWT secret 사용 금지
- [ ] OAuth redirect URI와 mobile deep link allowlist
- [ ] 모든 사용자 리소스의 소유권 테스트
- [ ] upload size/pixel/MIME/path traversal 테스트
- [ ] private image 접근과 URL 만료 테스트
- [ ] 로그 redaction 점검
- [ ] 탈퇴/삭제 workflow 검증
- [ ] provider credential rotation 절차
- [ ] dependency와 container vulnerability scan
- [ ] 개인정보 처리방침/약관 version과 동의 기록 정책
