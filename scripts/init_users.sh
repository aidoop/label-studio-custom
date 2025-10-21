#!/bin/bash

# ==============================================================================
# Label Studio 초기 사용자 생성 스크립트 (Bash wrapper)
# ==============================================================================

set -e  # 에러 발생 시 즉시 종료

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Label Studio 초기화 시작...${NC}"
echo ""

# 1. 마이그레이션 실행
echo -e "${YELLOW}1. 데이터베이스 마이그레이션 실행 중...${NC}"
python /label-studio/label_studio/manage.py migrate --noinput
echo ""

# 2. 초기 사용자 생성
echo -e "${YELLOW}2. 초기 사용자 생성 중...${NC}"
python /scripts/create_initial_users.py
echo ""

# 3. static 파일 수집 (선택사항)
# echo -e "${YELLOW}3. Static 파일 수집 중...${NC}"
# python /label-studio/label_studio/manage.py collectstatic --noinput
# echo ""

echo -e "${GREEN}초기화 완료!${NC}"
echo ""
echo "접속 정보:"
echo "  URL: http://label.nubison.localhost:8080"
echo ""
echo "관리자 계정:"
echo "  Email: admin@nubison.localhost"
echo "  Password: admin123"
echo ""
echo "일반 사용자 계정:"
echo "  user1@nubison.localhost / user123"
echo "  user2@nubison.localhost / user123"
echo "  annotator@nubison.localhost / annotator123"
echo ""
