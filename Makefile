.DEFAULT_GOAL := help

.PHONY: help install install-dev install-postgres db-up db-down db-logs db-status db-upgrade db-downgrade db-check run test lint format check

ifneq (,$(filter run,$(firstword $(MAKECMDGOALS))))
PORT := $(or $(word 2,$(MAKECMDGOALS)),8000)
$(eval $(PORT):;@:)
else
PORT := 8000
endif

help: ## 사용 가능한 명령 표시
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## 운영 의존성 설치
	uv sync

install-dev: ## 개발 및 테스트 의존성 설치
	uv sync --extra dev

install-postgres: install-dev ## 개발 의존성 및 PostgreSQL 드라이버 설치

db-up: ## PostgreSQL/pgvector 컨테이너 실행
	docker compose up -d postgres

db-down: ## PostgreSQL 컨테이너 중지
	docker compose down

db-logs: ## PostgreSQL 로그 확인
	docker compose logs -f postgres

db-status: ## PostgreSQL 컨테이너 상태 확인
	docker compose ps postgres

db-upgrade: ## DB 스키마를 최신 Alembic revision으로 업그레이드
	uv run alembic upgrade head

db-downgrade: ## DB 스키마를 한 revision 되돌리기
	uv run alembic downgrade -1

db-check: ## ORM metadata와 DB 스키마 차이 확인
	uv run alembic check

run: ## 개발 API 서버 실행 (기본 8000, 예: make run 9000)
	uv run uvicorn cloth_vision_api.main:app --reload --port $(PORT)

test: ## 테스트 실행
	uv run pytest

lint: ## 정적 검사 실행
	uv run ruff check .

format: ## 코드 포맷 적용
	uv run ruff format .

check: ## 포맷, 린트, 테스트 전체 검증
	uv run ruff format --check .
	uv run ruff check .
	uv run pytest
