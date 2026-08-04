# Cloth Vision Backend Roadmap

> 기준: `wireframe/`의 10개 화면과 현재 `cloth-vision`/`cloth-vision-core` 구현  
> 상세 분석: [`WIREFRAME_BACKEND_GAP_ANALYSIS.md`](WIREFRAME_BACKEND_GAP_ANALYSIS.md)

## 1. 현재 상태

현재 코드는 다음 범위까지 구현되어 있다.

- 이메일 회원가입/로그인과 JWT access token
- 사용자별 옷장 생성 및 조회
- 단일 의류 이미지 업로드와 로컬 저장
- 전체 이미지의 대표 색상 1개 추출
- 아이템 조회·수정·삭제
- 기준 아이템과 후보 아이템 간 1:1 조합 점수

화면설계서를 완성하려면 사용자 프로필, 실제 AI 분석, 검색 가능한 디지털 옷장, 다중
아이템 코디, 착용 리뷰와 집계 모델이 추가되어야 한다.

## 2. 판단 기준

### 우선순위

- **P0**: 핵심 사용자 흐름 또는 출시 화면을 막는 기능
- **P1**: P0 데이터가 쌓인 뒤 제품 가치를 높이는 기능
- **P2**: 외부 사업자나 고급 AI 처리가 필요하며 초기 검증에는 없어도 되는 기능

### 난이도

- **하**: 현재 모델이나 endpoint를 제한적으로 보강하는 작업
- **중**: DB migration과 여러 application layer 변경이 필요한 작업
- **상**: 새로운 도메인, 외부 연동, 비동기 처리 또는 AI 품질 검증이 포함되는 작업

난이도는 예상 기간이 아니라 현재 코드 대비 변경 범위와 기술적 불확실성을 뜻한다.

## 3. 화면별 우선순위와 난이도

| 화면/기능 | 우선순위 | 난이도 | 판단 |
|---|---:|---:|---|
| 로그인: Apple/Google/Kakao | P0 | 상 | 출시 화면에는 필요하지만 이메일 로그인으로 다른 기능 개발은 진행 가능 |
| 온보딩: 체형 프로필 | P0 | 중 | 추천 개인화의 입력값이며 profile schema/API가 필요 |
| 홈 대시보드 | P0 | 상 | 첫 진입 화면이지만 추천·착용 데이터가 먼저 구현되어야 함 |
| 옷장 채우기: 직접 촬영 | P0 | 중 | 핵심 데이터의 진입점이며 현재 단일 업로드 기반을 활용 가능 |
| AI 의류 분석 결과 | P0 | 상 | 실제 Vision, segmentation, 소재·팔레트, 비동기 job과 이미지 제공 필요 |
| 디지털 옷장 | P0 | 중 | 현재 목록 API에 이미지 URL, 필터, 검색, 정렬, pagination 보강 필요 |
| AI 코디 추천 | P0 | 상 | pairwise 점수를 다중 아이템 outfit과 문맥 기반 추천으로 확장해야 함 |
| 오늘의 코디 리뷰 | P0 | 중 | outfit 이후 wear event와 별점/tag/note 저장 필요 |
| 옷장 분석 | P1 | 상 | wear event와 가격 데이터가 쌓인 뒤 의미 있는 집계 가능 |
| 프로필/취향/AI 설정 | P1 | 중 | 기본 profile은 P0, 상세 설정 화면은 독립적으로 확장 가능 |
| 구독 관리 | P2 | 상 | 결제 provider, webhook 검증, entitlement 정책 필요 |
| 쇼핑 스크린샷/OOTD 가져오기 | P2 | 상 | 다중 아이템 검출, crop 확인, 외부 소스 정책 필요 |

## 4. 권장 구현 순서

우선순위가 같더라도 선행 데이터가 없으면 화면을 완성할 수 없으므로 다음 순서로
진행한다.

### 1단계. 기반 정리 — P0/중

- [x] Alembic 도입과 현재 DB baseline/목표 schema migration
- [ ] API enum, 오류 형식, 시간대와 삭제 정책 확정
- [ ] 업로드 이미지의 인증 조회 또는 signed URL 계약 정의

### 2단계. 사용자 프로필 — P0/중

- [x] `user_profiles`, `user_preferences` ORM/migration 추가
- [ ] 체형·키·성별 정체성·퍼스널 컬러 온보딩 저장/수정
- [ ] 회원가입 시 default closet 생성 정책 확정

### 3단계. 의류 등록과 디지털 옷장 — P0/상

- [x] `item_images`, `analysis_jobs`, `item_analyses` ORM/migration 추가
- [ ] 비동기 분석 상태와 실패/재시도 구현
- [ ] production Vision/segmentation 연결
- [ ] 분석 결과 사용자 보정 및 AI 원본 분리
- [ ] 이미지 URL, 검색, 카테고리 필터, 정렬, cursor pagination

### 4단계. 코디 추천과 착용 리뷰 — P0/상

- [x] `outfits`, `outfit_items` ORM/migration 추가
- [ ] 날씨·일정·취향 기반 다중 아이템 추천
- [ ] bookmark와 like/dislike 저장
- [x] `wear_events`, `outfit_reviews` ORM/migration 추가

### 5단계. 출시 화면 완성 — P0/상

- [ ] Apple/Google/Kakao OAuth
- [ ] refresh token rotation과 logout/revoke
- [ ] 추천·착용 데이터를 묶는 홈 dashboard endpoint

### 6단계. 분석과 설정 확장 — P1/상

- [ ] 컬러/계절 분포, 미착용 아이템, 착용당 비용
- [ ] 옷장 점수와 부족 아이템 추천 규칙
- [ ] 상세 취향과 AI 설정

### 7단계. 사업 및 고급 입력 기능 — P2/상

- [ ] 결제 provider와 구독 entitlement
- [ ] 쇼핑 스크린샷 다중 상품 분석
- [ ] OOTD 가져오기

## 5. 첫 번째 목표 Vertical Slice

첫 구현 목표는 기능 개수보다 아래 흐름이 실제 DB와 API를 통해 끝까지 이어지는 것이다.

```text
이메일 로그인
→ 체형 프로필 저장
→ 사진 1장 업로드
→ AI 분석 완료 및 사용자 보정
→ 디지털 옷장에서 조회
→ 보유 의류 기반 다중 아이템 코디 추천
→ 오늘 입기
→ 리뷰 저장
→ 홈과 옷장 분석에 착용 데이터 반영
```

이 흐름의 통합 테스트가 통과한 뒤 소셜 로그인, 고급 분석, 구독과 외부 import를
확장한다.

## 6. 진척도 관리 규칙

- `[ ]`: 시작 전
- `[-]`: 진행 중
- `[x]`: 구현과 검증 완료
- endpoint만 추가된 상태는 완료로 표시하지 않는다.
- DB migration, 소유권 검사, 오류 처리와 관련 테스트까지 통과해야 완료로 표시한다.
- 요구사항이 바뀌면 완료 항목을 억지로 유지하지 않고 다시 검토한다.
