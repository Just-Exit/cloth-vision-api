# 비기능 요구사항

## 1. 범위

이 문서는 화면설계서 기능을 운영 가능한 품질로 제공하기 위한 최소 기준을 정의한다.
구체적인 수치는 부하 시험과 provider 선택 후 조정하되, 변경 시 근거를 기록한다.

## 2. 성능

| ID | 우선순위 | 요구사항 |
|---|---:|---|
| NFR-PERF-001 | P0 | AI provider를 호출하지 않는 일반 API의 서버 p95는 로컬 네트워크 제외 500ms 이내를 목표로 한다. |
| NFR-PERF-002 | P0 | 아이템 목록은 cursor pagination을 사용하고 기본 30개, 최대 100개로 제한한다. |
| NFR-PERF-003 | P0 | 이미지 업로드 요청은 파일 저장과 job 생성 후 빠르게 `202`를 반환하며 실제 AI 처리를 기다리지 않는다. |
| NFR-PERF-004 | P0 | thumbnail을 별도로 생성하고 원본 이미지를 목록 화면에서 직접 전송하지 않는다. |
| NFR-PERF-005 | P1 | dashboard와 analytics는 반복 계산을 피하도록 cache 또는 read model을 사용한다. |

## 3. 가용성과 복원력

| ID | 우선순위 | 요구사항 |
|---|---:|---|
| NFR-REL-001 | P0 | AI/weather/LLM 장애가 인증·옷장 조회까지 전파되지 않아야 한다. |
| NFR-REL-002 | P0 | analysis job은 timeout과 제한된 retry를 가지며 최종 실패 상태를 사용자에게 제공한다. |
| NFR-REL-003 | P0 | job 재전달과 모바일 중복 탭에도 item/wear event가 중복 생성되지 않아야 한다. |
| NFR-REL-004 | P0 | DB 변경은 migration으로 적용하고 배포 전 upgrade를 검증한다. |
| NFR-REL-005 | P1 | 외부 provider 실패 시 마지막 유효 데이터 또는 기능별 fallback을 제공한다. |

권장 job 상태:

```text
queued → running → succeeded
                 ↘ failed
queued/running → cancelled
```

## 4. 보안과 개인정보

| ID | 우선순위 | 요구사항 |
|---|---:|---|
| NFR-SEC-001 | P0 | 모든 사용자 리소스는 인증과 소유권 검사를 거친다. |
| NFR-SEC-002 | P0 | 비밀번호는 Argon2id, refresh token은 원문이 아닌 hash로 저장한다. |
| NFR-SEC-003 | P0 | 원본·파생 이미지는 private 저장소에 두고 signed URL 또는 인증 endpoint로 제공한다. |
| NFR-SEC-004 | P0 | 위치·체형·리뷰는 목적에 필요한 최소 정보만 수집한다. |
| NFR-SEC-005 | P0 | access/refresh token, provider credential, 이미지와 리뷰 노트는 로그에 기록하지 않는다. |
| NFR-SEC-006 | P0 | OAuth와 결제 webhook은 signature, issuer, audience, nonce/replay를 검증한다. |

세부 통제는 [`SECURITY.md`](SECURITY.md)를 따른다.

## 5. 데이터 정합성

- 모든 timestamp는 DB에 UTC로 저장하고 API에서 timezone을 명시한다.
- 금액은 float가 아니라 fixed precision numeric과 ISO currency code를 사용한다.
- 사용자 확정 item 값과 AI 분석 원본을 덮어쓰지 않고 분리한다.
- wear count와 last worn을 cache하면 원장인 `wear_events`에서 재생성할 수 있어야 한다.
- 추천과 옷장 점수는 scoring/pipeline version을 보존한다.
- hard delete가 필요한 개인정보와 통계 보존용 익명화 범위를 구분한다.

## 6. 확장성과 유지보수성

- HTTP/DB/JWT/환경설정은 API 저장소, provider-neutral 분석·matching은 Core에 둔다.
- Vision, weather, object storage, payment provider는 port/adapter 뒤에 둔다.
- provider SDK 타입을 domain/application 계층에 노출하지 않는다.
- API 변경은 가능한 한 additive하게 하고 breaking change는 버전 경계를 둔다.
- JSON 필드는 실험적 값에 사용하되 검색·제약이 중요한 값은 명시 컬럼으로 승격한다.

## 7. 관측성

모든 요청과 비동기 작업은 다음 상관관계를 제공해야 한다.

- request ID
- user-safe error code
- analysis/import job ID
- provider와 pipeline version
- 소요 시간과 retry 횟수

최소 지표:

- HTTP route별 latency/error rate
- analysis job queue time, runtime, success/failure rate
- AI/weather/OAuth/payment provider latency/error rate
- 업로드 크기와 validation 실패율
- 추천 생성 수, wear 전환 수, review 제출 수

## 8. 접근성과 국제화 지원

- API enum과 오류 코드는 언어 중립적으로 유지하고 한국어 문구를 식별자로 사용하지 않는다.
- 날짜/날씨/단위는 사용자 timezone과 locale을 고려한다.
- 키는 서버 내부에서 cm로 정규화하고 표시 단위 변환은 클라이언트 계약으로 구분한다.
- 색상 정보는 HEX만 반환하지 않고 이름 또는 semantic token을 함께 제공한다.

## 9. 호환성과 배포

- Python 3.11 이상을 지원한다.
- 운영 기준 DB는 PostgreSQL이며 SQLite는 빠른 단위/통합 테스트 용도로만 사용한다.
- migration은 PostgreSQL에서 별도 검증한다.
- object storage와 queue가 없어도 local adapter로 핵심 흐름을 개발할 수 있어야 한다.
- 환경별 secret은 코드와 이미지에 포함하지 않는다.

## 10. 완료 검증

비기능 요구사항은 다음 산출물로 검증한다.

- 부하/latency 측정 결과
- migration upgrade와 복구 rehearsal
- provider timeout/retry fault injection test
- 권한과 파일 업로드 보안 테스트
- 개인정보 로그 점검
- PostgreSQL 통합 테스트
- backup/restore 절차와 운영 runbook
