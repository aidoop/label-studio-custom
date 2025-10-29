#!/bin/bash
# Custom Export API 테스트 실행 스크립트

set -e

echo "================================================"
echo "Custom Export API 테스트 실행"
echo "================================================"

# Docker Compose로 환경 시작
echo ""
echo "[1/4] Docker 환경 시작 중..."
docker compose -f docker-compose.test.yml up -d postgres

# PostgreSQL 준비 대기
echo ""
echo "[2/4] PostgreSQL 준비 대기 중..."
sleep 10

# Label Studio 빌드 및 시작
echo ""
echo "[3/4] Label Studio 빌드 및 시작 중..."
docker compose -f docker-compose.test.yml up -d --build labelstudio

# Label Studio 준비 대기
echo ""
echo "Label Studio 초기화 대기 중 (60초)..."
sleep 60

# 테스트 실행
echo ""
echo "[4/4] 테스트 실행 중..."
echo "================================================"
docker compose -f docker-compose.test.yml exec -T labelstudio \
  bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.CustomExportAPITest --verbosity=2 --keepdb"

TEST_RESULT=$?

echo ""
echo "================================================"
if [ $TEST_RESULT -eq 0 ]; then
  echo "✅ 모든 테스트 성공!"
else
  echo "❌ 테스트 실패!"
fi
echo "================================================"

# 로그 확인 옵션
echo ""
echo "Docker 로그를 확인하려면:"
echo "  docker compose -f docker-compose.test.yml logs -f labelstudio"
echo ""
echo "환경을 종료하려면:"
echo "  docker compose -f docker-compose.test.yml down"

exit $TEST_RESULT
