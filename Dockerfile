# Label Studio with SSO Support
# 베이스 이미지: 공식 Label Studio 1.20.0
FROM heartexlabs/label-studio:1.20.0

# 메타데이터
LABEL maintainer="heartyoh@hatiolab.com"
LABEL description="Label Studio 1.20.0 with label-studio-sso integration"
LABEL version="1.20.0-sso"

# 작업 디렉토리 설정
WORKDIR /label-studio

# label-studio-sso 패키지 설치
# v6.0.7 버전 사용 (Native JWT 방식)
RUN pip install --no-cache-dir label-studio-sso==6.0.7

# PostgreSQL 클라이언트 라이브러리가 이미 설치되어 있음 (공식 이미지에 포함)
# 추가 패키지가 필요한 경우 여기에 설치
# RUN pip install --no-cache-dir <package-name>

# 커스텀 설정 파일을 복사 (선택사항)
# ConfigMap이나 Volume으로 런타임에 주입하는 것을 권장하지만,
# 이미지에 포함시키려면 아래 주석을 해제하세요
# COPY config/label_studio.py /label-studio/label_studio/core/settings/
# COPY config/urls.py /label-studio/label_studio/core/

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 기본 포트 노출 (공식 이미지와 동일)
EXPOSE 8080

# 엔트리포인트는 베이스 이미지 것을 그대로 사용
# CMD는 베이스 이미지에 정의되어 있음
