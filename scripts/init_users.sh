#!/bin/bash

# ==============================================================================
# Label Studio 초기 사용자 및 Organization 생성 스크립트
# ==============================================================================
#
# 다음을 자동으로 생성합니다:
# - 관리자 및 일반 사용자
# - Organization
# - Organization 멤버십
# - Admin API 토큰
#
# 사용법:
#   docker compose exec labelstudio bash /scripts/init_users.sh
#
# ==============================================================================

set -e  # 에러 발생 시 즉시 종료

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}  Label Studio 초기화 스크립트${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# 1. 마이그레이션 실행
echo -e "${YELLOW}Step 1: 데이터베이스 마이그레이션 실행 중...${NC}"
python /label-studio/label_studio/manage.py migrate --noinput
echo ""

# 2. 초기 사용자 및 Organization 생성
echo -e "${YELLOW}Step 2: 사용자 및 Organization 초기화 중...${NC}"
echo ""
python /scripts/create_initial_users.py
echo ""

echo -e "${GREEN}========================================================================${NC}"
echo -e "${GREEN}  초기화 완료!${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo ""
