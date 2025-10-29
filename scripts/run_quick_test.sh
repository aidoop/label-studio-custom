#!/bin/bash
# Custom Export API 빠른 테스트 스크립트
# 이미 실행 중인 Docker 환경에서 특정 테스트만 실행

set -e

if [ -z "$1" ]; then
  echo "사용법: $0 <test_method_name>"
  echo ""
  echo "예시:"
  echo "  $0 test_export_with_date_filter"
  echo "  $0 test_export_with_timezone_aware_dates"
  echo "  $0 test_export_with_kst_timezone_filter"
  echo "  $0 test_export_with_naive_datetime"
  echo "  $0 test_export_with_mixed_timezone_formats"
  echo "  $0 test_export_date_boundary_conditions"
  echo ""
  echo "모든 테스트 실행:"
  echo "  $0 all"
  exit 1
fi

TEST_NAME=$1

echo "================================================"
echo "Custom Export API 테스트 실행: $TEST_NAME"
echo "================================================"

if [ "$TEST_NAME" = "all" ]; then
  docker compose -f docker-compose.test.yml exec -T labelstudio \
    bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.CustomExportAPITest --verbosity=2 --keepdb"
else
  docker compose -f docker-compose.test.yml exec -T labelstudio \
    bash -c "cd /label-studio/label_studio && python manage.py test custom_api.tests.CustomExportAPITest.$TEST_NAME --verbosity=2 --keepdb"
fi

TEST_RESULT=$?

echo ""
echo "================================================"
if [ $TEST_RESULT -eq 0 ]; then
  echo "✅ 테스트 성공!"
else
  echo "❌ 테스트 실패!"
fi
echo "================================================"

exit $TEST_RESULT
