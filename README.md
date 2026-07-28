# AI Fashion Coach

Explainable AI 기반 개인 맞춤 패션 분석 플랫폼

## Goal

사용자의 의류 사진을 분석하고
옷장 데이터를 구축하여
개인 맞춤 코디 추천 제공

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

현재 저장소는 FastAPI 기반 REST API 서버만 포함합니다. 헥사고날 아키텍처로 도메인과
애플리케이션 계층을 프레임워크 및 외부 인프라로부터 분리했습니다.

구현 범위:

- 사용자 및 옷장 생성/조회
- 의류 이미지 업로드와 형식·해상도 검증
- 대표 색상과 초기 태그를 산출하는 경량 분석
- 분석 결과 조회 및 사용자 수정
- 색상·계절·스타일 기반 기본 의류 조합 추천
- PostgreSQL 및 pgvector 기반 로컬 개발 환경

실제 의류 분할·분류·Embedding 모델은 MVP 분석 포트를 교체해 연결하도록 남겨 두었습니다.

상세 설계 및 요구사항 문서는 [`guide/`](guide/) 디렉터리에 있습니다.

## 실행

Python 3.11 이상과 `uv` 사용을 권장합니다.

```bash
uv sync --extra dev
uv run uvicorn cloth_vision.main:app --reload
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

## 테스트

```bash
uv run pytest
uv run ruff check .
```

전체 검증은 `make check`로 실행할 수 있습니다.
