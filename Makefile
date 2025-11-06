# Label Studio Custom - Makefile
# 개발 및 테스트 편의성을 위한 명령어 모음

.PHONY: help build up down logs test test-quick test-all clean test-date test-timezone test-kst test-sso test-sso-token test-sso-batch restart

# 기본 명령어: help
help:
	@echo "=========================================="
	@echo "Label Studio Custom - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "Docker 관리:"
	@echo "  make build       - Docker 이미지 빌드"
	@echo "  make up          - 테스트 환경 시작 (백그라운드)"
	@echo "  make down        - 테스트 환경 중지"
	@echo "  make restart     - 테스트 환경 재시작"
	@echo "  make logs        - 로그 확인 (실시간)"
	@echo "  make clean       - 모든 컨테이너, 볼륨 삭제"
	@echo ""
	@echo "테스트:"
	@echo "  make test        - 전체 테스트 실행 (환경 시작부터)"
	@echo "  make test-quick  - 빠른 테스트 (환경이 실행 중일 때)"
	@echo "  make test-all    - 모든 Custom Export API 테스트"
	@echo "  make test-sso    - 모든 SSO Token Validation API 테스트"
	@echo "  make test-sso-token  - Single SSO Token API 테스트"
	@echo "  make test-sso-batch  - Batch SSO Token API 테스트"
	@echo "  make test-date   - 날짜 필터 테스트만 실행"
	@echo "  make test-timezone - 타임존 테스트만 실행"
	@echo "  make test-kst    - KST 타임존 테스트만 실행"
	@echo ""

# Docker 관리
build:
	@echo "🔨 Docker 이미지 빌드 중..."
	docker compose -f docker-compose.test.yml build

up:
	@echo "🚀 테스트 환경 시작 중..."
	docker compose -f docker-compose.test.yml up -d
	@echo "⏳ Label Studio 초기화 대기 중 (30초)..."
	@sleep 30
	@echo "✅ 테스트 환경 준비 완료!"

down:
	@echo "🛑 테스트 환경 중지 중..."
	docker compose -f docker-compose.test.yml down

restart: down up

logs:
	@echo "📋 로그 확인 (Ctrl+C로 종료)..."
	docker compose -f docker-compose.test.yml logs -f labelstudio

clean:
	@echo "🧹 모든 컨테이너 및 볼륨 삭제 중..."
	docker compose -f docker-compose.test.yml down -v
	@echo "✅ 정리 완료!"

# 테스트 실행
test:
	@echo "🧪 전체 테스트 실행 (환경 시작부터)..."
	@bash scripts/run_tests.sh

test-quick:
	@echo "⚡ 빠른 테스트 실행..."
	@bash scripts/run_quick_test.sh all

test-all:
	@echo "🧪 모든 Custom Export API 테스트 실행..."
	@docker compose -f docker-compose.test.yml exec -T labelstudio \
		bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.CustomExportAPITest --verbosity=2 --keepdb"

# 특정 테스트 실행
test-date:
	@echo "📅 날짜 필터 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_with_date_filter

test-timezone:
	@echo "🌍 타임존 aware 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_with_timezone_aware_dates

test-kst:
	@echo "🇰🇷 KST 타임존 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_with_kst_timezone_filter

test-naive:
	@echo "⏰ Naive datetime 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_with_naive_datetime

test-mixed:
	@echo "🔀 Mixed timezone 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_with_mixed_timezone_formats

test-boundary:
	@echo "🎯 Boundary conditions 테스트 실행..."
	@bash scripts/run_quick_test.sh test_export_date_boundary_conditions

# SSO Token Validation API 테스트
test-sso:
	@echo "🔐 모든 SSO Token Validation API 테스트 실행..."
	@docker compose -f docker-compose.test.yml exec -T labelstudio \
		bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.ValidatedSSOTokenAPITest custom_api.tests.BatchValidateSSOTokenAPITest --verbosity=2 --keepdb"

test-sso-token:
	@echo "🔑 Single SSO Token API 테스트 실행..."
	@docker compose -f docker-compose.test.yml exec -T labelstudio \
		bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.ValidatedSSOTokenAPITest --verbosity=2 --keepdb"

test-sso-batch:
	@echo "🔑 Batch SSO Token API 테스트 실행..."
	@docker compose -f docker-compose.test.yml exec -T labelstudio \
		bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.BatchValidateSSOTokenAPITest --verbosity=2 --keepdb"

# 개발 편의 명령어
shell:
	@echo "🐚 Label Studio 컨테이너 접속..."
	docker compose -f docker-compose.test.yml exec labelstudio bash

db-shell:
	@echo "🗄️  PostgreSQL 접속..."
	docker compose -f docker-compose.test.yml exec postgres psql -U postgres -d labelstudio
