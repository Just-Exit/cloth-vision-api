# Cloth Vision API

Explainable AI 기반 개인 맞춤 패션 분석 플랫폼

## Goal

사용자의 의류 사진을 분석하고 옷장 데이터를 구축하여
개인 맞춤 코디 추천 제공 및 착장 분석

## Tech Stack

Frontend:

- React Native
- TypeScript

Backend:

- Python
- FastAPI

AI:

- OpenCV
- Vision Model
- Embedding Model
- LLM

Database:

- PostgreSQL
- pgvector

## Backend MVP

FastAPI 기반 Cloth Vision 서비스 API입니다. 이미지 분석·점수화·매칭은 별도
[`cloth-vision-core`](https://github.com/onedayonecommit/cloth-vision-core) 패키지에
위임하고, 이 저장소는 HTTP API, 인증, DB, 이미지 저장을 담당합니다.

구현 범위:

- 이메일·비밀번호 회원가입, JWT 로그인 및 현재 사용자 조회
- 사용자별 closet 생성/조회와 소유권 검사
- 옷·신발·액세서리를 포함한 fashion item 이미지 업로드와 형식·해상도 검증
- 전체 이미지의 대표 색상 1개를 산출하는 경량 분석
- 분석 결과 조회 및 사용자 수정
- 색상·계절·스타일 기반 기본 패션 아이템 조합 추천
- PostgreSQL/pgvector 이미지 기반 로컬 개발 환경

현재(2026-08-04) 분석 파이프라인에는 production Vision provider가 연결되어 있지 않습니다. 업로드 시
카테고리 힌트를 전달하지 않으면 카테고리는 `unknown`, 하위 카테고리는 `unclassified`가
되며 스타일·계절 태그도 자동 생성되지 않습니다. 실제 의류 분할·분류·소재 분석과
Embedding 저장은 구현 예정입니다.

인증 정보는 `users`와 `auth_identities`로 분리되어 있습니다. 현재 로컬 비밀번호 로그인을
지원하며, 추후 Google·Apple OAuth는 provider와 외부 subject 기반 identity를 추가해
확장할 수 있습니다. 비밀번호는 Argon2id 해시로만 저장됩니다.

상세 설계 및 요구사항 문서는 [`guide/`](guide/) 디렉터리에 있습니다.

## 문서

- [`ROADMAP.md`](ROADMAP.md): 화면설계서 기준 우선순위, 난이도, 구현 순서와 진척도
- [`WIREFRAME_BACKEND_GAP_ANALYSIS.md`](WIREFRAME_BACKEND_GAP_ANALYSIS.md): 화면별 API·DB
  충족 여부, 목표 ERD와 상세 작업
- [`guide/`](guide/): 아키텍처, API와 프로젝트 설계 자료

## 저장소 구성

로컬에서 API와 Core를 함께 개발할 때 두 저장소를 같은 상위 디렉터리에 둡니다.

```bash
git clone git@github.com:onedayonecommit/cloth-vision-api.git cloth-vision
git clone git@github.com:onedayonecommit/cloth-vision-core.git
```

```text
workspace/
└── cloth/
    ├── cloth-vision/
    └── cloth-vision-core/
```

API의 `pyproject.toml`은 개발 중 `../cloth-vision-core`를 editable dependency로
사용합니다. Core `v0.1.0`을 공개한 뒤에는 Git tag 또는 PyPI 버전 의존성으로 전환할 수
있습니다.

## 실행

Python 3.11 이상과 `uv` 사용을 권장합니다.

```bash
uv sync --extra dev
uv run uvicorn cloth_vision_api.main:app --reload
```

프로젝트 디렉터리를 이동했다면 기존 `.venv/bin/*` 실행 파일에 이전 절대경로가 남을 수
있습니다. 이 경우 가상환경을 새로 생성합니다.

```bash
mv .venv .venv.before-move
uv sync --extra dev
```

또는 Make를 사용할 수 있습니다.

```bash
make install-dev
make run
```

기본 포트는 `8000`이며 실행 명령 뒤에 포트를 지정할 수 있습니다.

```bash
make run 9000
```

- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `GET http://127.0.0.1:8000/api/v1/health`

PostgreSQL은 Docker Compose로 실행합니다.

```bash
cp .env.example .env
make install-dev
make db-up
make run
```

기본 접속 정보는 로컬 개발 전용이며 `.env`에서 변경할 수 있습니다.

```text
Host: localhost
Port: 5432
Database: cloth_vision
User: cloth_vision
Password: cloth_vision
```

컨테이너 상태와 로그는 각각 `make db-status`, `make db-logs`로 확인합니다. 데이터는
Docker named volume인 `postgres_data`에 유지됩니다.

DB schema는 Alembic migration으로 관리합니다.

```bash
make db-upgrade
make db-check
```

이전 `create_all()` 방식으로 만든 DB는 기존 네 테이블의 컬럼 계약이 정확히 일치할 때만
`0001` revision으로 자동 stamp한 뒤 업그레이드합니다. 운영자가 직접 전환하는 절차는
[`migrations/README.md`](migrations/README.md)를 참고합니다.

## 테스트

```bash
uv run pytest
uv run ruff check .
```

전체 검증은 `make check`로 실행할 수 있습니다.
