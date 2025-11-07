# Label Studio with SSO Support
# 베이스 이미지: 공식 Label Studio 1.20.0
FROM heartexlabs/label-studio:1.20.0

# 메타데이터
LABEL maintainer="heartyoh@hatiolab.com"
LABEL description="Label Studio 1.20.0 with label-studio-sso integration"
LABEL version="1.20.0-sso.27"

# 작업 디렉토리 설정
WORKDIR /label-studio

# 로컬 label-studio-sso 패키지 설치
# 커스텀 미들웨어 수정 버전 (JWT 우선 인증 - 기존 세션 무시)
COPY label_studio_sso-6.0.8-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/label_studio_sso-6.0.8-py3-none-any.whl

# PostgreSQL 클라이언트 라이브러리가 이미 설치되어 있음 (공식 이미지에 포함)
# 추가 패키지가 필요한 경우 여기에 설치
# RUN pip install --no-cache-dir <package-name>

# 커스텀 설정 파일 복사
COPY config/label_studio.py /label-studio/label_studio/core/settings/label_studio.py
COPY config/urls_simple.py /label-studio/label_studio/core/urls.py
COPY config/security_middleware.py /label-studio/label_studio/core/settings/security_middleware.py

# 커스텀 permissions 및 API 복사
COPY custom-permissions /label-studio/label_studio/custom_permissions
COPY custom-api /label-studio/label_studio/custom_api

# 커스텀 템플릿 복사 (hideHeader 기능)
COPY custom-templates/base.html /label-studio/label_studio/templates/base.html

# Webhook payload enrichment 패치 적용
# Label Studio의 실제 webhooks/utils.py에 completed_by_info 추가 로직 삽입
COPY scripts/patch_webhooks.py /tmp/patch_webhooks.py
RUN python3 /tmp/patch_webhooks.py

# 정적 파일 수집
# Label Studio의 JavaScript, CSS 등 정적 파일을 수집하여 /label-studio/label_studio/core/ 디렉토리로 복사
# 이 과정이 없으면 sw.js, main.js 등의 파일을 찾을 수 없어 404 오류 발생
RUN cd /label-studio/label_studio && \
    python3 manage.py collectstatic --noinput

# 초기화 스크립트 복사
COPY --chmod=755 scripts /scripts

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 기본 포트 노출 (공식 이미지와 동일)
EXPOSE 8080

# 엔트리포인트는 베이스 이미지 것을 그대로 사용
# CMD는 베이스 이미지에 정의되어 있음
