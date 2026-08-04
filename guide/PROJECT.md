# Cloth Vision 프로젝트 정의

## 1. 제품 목표

Cloth Vision은 사용자가 보유한 의류를 디지털 옷장으로 만들고, 체형·취향·날씨·일정과
실제 착용 피드백을 이용해 설명 가능한 코디를 추천하는 서비스다.

핵심 사용자 루프는 다음과 같다.

```text
로그인과 프로필 설정
→ 의류 촬영 및 분석
→ 분석 결과 확인·보정
→ 디지털 옷장 저장
→ 보유 의류 기반 코디 추천
→ 실제 착용과 리뷰
→ 다음 추천 및 옷장 분석 개선
```

## 2. 화면설계서 범위

현재 제품 범위는 `wireframe/`의 다음 10개 화면을 기준으로 한다.

| 화면 | 제품 목적 | 백엔드 핵심 |
|---|---|---|
| 로그인 | 계정 진입 | local/social auth와 session |
| 온보딩: 체형 프로필 | 개인화 입력 수집 | profile과 onboarding 상태 |
| 홈 대시보드 | 오늘의 핵심 정보 요약 | 날씨·코디·착용·최근 아이템 집계 |
| 옷장 채우기 | 의류 데이터 수집 | upload/import와 analysis job |
| AI 의류 분석 결과 | 분석 확인과 사용자 보정 | image/analysis provenance와 item 확정값 |
| 디지털 옷장 | 보유 의류 탐색 | 검색·필터·정렬·pagination |
| 옷장 분석 | 활용 습관 이해 | wear event 기반 analytics |
| AI 코디 추천 | 상황별 다중 아이템 추천 | outfit, scoring, explanation |
| 오늘의 코디 리뷰 | 착용 경험 피드백 | wear event와 review |
| 프로필 | 계정·취향·구독 관리 | profile/preferences/subscription |

화면에 표시된 온보딩 5단계 중 현재 확인 가능한 것은 체형 프로필 단계 하나뿐이다.
나머지 단계는 화면과 제품 결정이 확정된 후 범위에 추가한다.

## 3. 현재 구현 상태

현재 백엔드는 초기 수직 슬라이스다.

구현됨:

- 이메일 회원가입/로그인과 JWT access token
- 사용자, 인증 identity, 옷장, 아이템 영속화
- 단일 이미지 업로드와 로컬 파일 저장
- 이미지 검증과 전체 이미지 대표색 1개 추출
- 아이템 CRUD와 소유권 검사
- 아이템 두 개의 색상·계절·스타일·카테고리 점수

아직 구현되지 않음:

- social OAuth, refresh/logout
- 사용자 체형/퍼스널 컬러/취향
- production Vision, segmentation, 소재와 다색 팔레트 분석
- 비동기 분석 job과 파생 이미지
- 다중 아이템 outfit과 추천 결과 영속화
- 착용 이력, 리뷰, dashboard, wardrobe analytics
- subscription과 screenshot/OOTD import

현재 구현과 화면 요구사항의 상세 비교는
[`../WIREFRAME_BACKEND_GAP_ANALYSIS.md`](../WIREFRAME_BACKEND_GAP_ANALYSIS.md)를 따른다.

## 4. MVP 범위

### MVP에 포함

- 이메일 로그인과 최소 1개 social provider
- 체형 프로필 저장과 수정
- 직접 촬영한 의류 1개 업로드
- 비동기 분석 상태와 사용자가 보정 가능한 결과
- 이미지가 표시되는 검색 가능한 디지털 옷장
- 보유 의류로 구성된 다중 아이템 코디
- 코디 저장, like/dislike, 오늘 입기
- 별점·quick tag·노트 리뷰
- 핵심 홈 dashboard

### MVP 이후

- 정교한 옷장 분석 리포트
- 쇼핑 스크린샷 다중 상품 추출
- 외부 OOTD 서비스 연동
- 유료 구독과 entitlement
- 생성형 의류 이미지, 3D avatar, virtual try-on

## 5. 제품 원칙

1. 추천은 사용자가 실제 보유하고 사용 가능한 아이템을 우선한다.
2. 사용자가 확정한 값과 AI 원본 결과를 분리해 보존한다.
3. 점수는 deterministic code가 계산하고 LLM은 설명만 생성한다.
4. 이미지에서 확정하기 어려운 소재 비율 등은 AI 추정임을 표시한다.
5. 원본 이미지는 보존하고 파생 이미지는 별도 artifact로 관리한다.
6. 사용자의 체형, 위치, 취향과 리뷰는 필요한 만큼만 수집한다.
7. 화면용 숫자는 계산 근거와 버전을 추적할 수 있어야 한다.

## 6. 저장소 책임

```text
React Native
    ↓ HTTP
cloth-vision
    ├── 인증·인가
    ├── 사용자/옷장/outfit API
    ├── DB와 migration
    ├── 이미지 저장
    ├── 비동기 job 조정
    └── 외부 provider adapter
    ↓ Python API
cloth-vision-core
    ├── 이미지 검증·정규화
    ├── provider-neutral 분석 pipeline
    ├── matching/scoring
    └── 설명 가능한 구조화 결과
```

FastAPI, SQLAlchemy, JWT, 사용자 CRUD와 외부 서비스 설정은 `cloth-vision` 책임이다.
재사용 가능한 이미지 분석과 deterministic matching은 `cloth-vision-core` 책임이다.

## 7. 성공 기준

첫 번째 제품 성공 기준은 다음 흐름이 통합 테스트로 끝까지 동작하는 것이다.

```text
이메일 로그인
→ 체형 프로필 저장
→ 사진 업로드
→ 분석 완료와 보정
→ 옷장 조회
→ 다중 아이템 코디 추천
→ 오늘 입기
→ 리뷰
→ dashboard 반영
```

정량 제품 지표는 별도 제품 결정이 필요하지만 최소한 아래를 관찰할 수 있어야 한다.

- 업로드 대비 분석 완료율
- 분석 결과 사용자 수정률
- 추천 조회 대비 오늘 입기 전환율
- 착용 대비 리뷰 제출률
- 추천 like/dislike 비율
- 7일/30일 옷장 재방문율

## 8. 관련 문서

- [`../ROADMAP.md`](../ROADMAP.md): 우선순위, 난이도와 진척도
- [`FUNCTIONAL_REQUIREMENTS.md`](FUNCTIONAL_REQUIREMENTS.md): 화면별 기능 요구사항
- [`NON_FUNCTIONAL_REQUIREMENTS.md`](NON_FUNCTIONAL_REQUIREMENTS.md): 품질 요구사항
- [`ARCHITECTURE.md`](ARCHITECTURE.md): 시스템 구조와 흐름
- [`DOMAIN.md`](DOMAIN.md): 도메인 모델과 불변식
- [`DATABASE.md`](DATABASE.md): 현재/목표 DB 구조
- [`API.md`](API.md): 현재/목표 HTTP 계약
- [`AI_PIPELINE.md`](AI_PIPELINE.md): 의류 분석 pipeline
- [`RECOMMENDATION.md`](RECOMMENDATION.md): 코디 추천과 점수화
- [`SECURITY.md`](SECURITY.md): 인증·이미지·개인정보 보안
- [`TESTING.md`](TESTING.md): 검증 전략과 완료 기준
