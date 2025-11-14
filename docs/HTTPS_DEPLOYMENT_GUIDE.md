# HTTPS 배포 가이드

Label Studio Custom을 HTTPS 환경(프로덕션/개발 서버)에 배포할 때 필요한 설정 가이드입니다.

## 목차

- [문제 상황](#문제-상황)
- [원인 분석](#원인-분석)
- [해결 방법](#해결-방법)
- [설정 예시](#설정-예시)
- [검증 방법](#검증-방법)
- [트러블슈팅](#트러블슈팅)

---

## 문제 상황

### 증상

로컬 개발 환경(HTTP)에서는 SSO 로그인이 정상 작동하지만, HTTPS 환경(프로덕션/개발 서버)에서는 다음과 같은 문제가 발생합니다:

- ❌ JWT 토큰은 발급되지만 Label Studio에서 인증되지 않음
- ❌ `ls_sessionid` 쿠키는 있지만 로그인 처리가 안 됨
- ❌ iframe에서 Label Studio 접근 시 로그인 페이지가 계속 표시됨
- ❌ 직접 Label Studio URL 접근 시에도 로그인이 유지되지 않음

### 환경 비교

| 환경 | 프로토콜 | 도메인 예시 | 상태 |
|------|---------|------------|------|
| 로컬 개발 | HTTP | `http://label.nubison.localhost:8080` | ✅ 정상 |
| 개발 서버 | HTTPS | `https://label-dev.nubison.io` | ❌ 실패 |
| 프로덕션 | HTTPS | `https://label.nubison.io` | ❌ 실패 |

---

## 원인 분석

### 핵심 원인: 쿠키 Secure Flag 미설정

HTTPS 환경에서는 브라우저 보안 정책에 따라 **쿠키에 `Secure` 플래그가 필수**입니다.

```
HTTP 환경:
  쿠키 설정: domain=.nubison.localhost, secure=false
  → ✅ 브라우저가 쿠키 저장 및 전송

HTTPS 환경:
  쿠키 설정: domain=.nubison.io, secure=false
  → ❌ 브라우저가 쿠키 저장은 하지만 전송하지 않음
  → ❌ Label Studio가 JWT 토큰을 받지 못함
  → ❌ 세션 생성 실패
```

### 관련 쿠키

Label Studio에서 사용하는 주요 쿠키:

| 쿠키 이름 | 용도 | Secure 필요 여부 |
|-----------|------|-----------------|
| `ls_auth_token` | JWT SSO 토큰 | ✅ 필수 |
| `ls_sessionid` | Django 세션 ID | ✅ 필수 |
| `ls_csrftoken` | CSRF 보호 토큰 | ✅ 필수 |

---

## 해결 방법

### 1단계: Label Studio 환경변수 설정

**docker-compose.yml 또는 환경변수 파일 수정**:

```yaml
services:
  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.36
    environment:
      # ============================================================
      # HTTPS 환경 필수 설정
      # ============================================================

      # 1. 쿠키 Secure Flag 활성화
      SESSION_COOKIE_SECURE: true    # 또는 1, yes, on
      CSRF_COOKIE_SECURE: true       # 또는 1, yes, on

      # 2. 쿠키 도메인 설정 (서브도메인 간 공유)
      SESSION_COOKIE_DOMAIN: .nubison.io
      CSRF_COOKIE_DOMAIN: .nubison.io

      # 3. Label Studio 호스트 URL
      LABEL_STUDIO_HOST: https://label-dev.nubison.io

      # 4. iframe 허용 설정 (SSO 콘솔용)
      CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io"

      # ============================================================
      # 기타 필수 설정
      # ============================================================

      # 데이터베이스
      DJANGO_DB: default
      POSTGRES_HOST: postgres
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your-password

      # SSO 설정
      JWT_SSO_COOKIE_NAME: ls_auth_token
      JWT_SSO_NATIVE_USER_ID_CLAIM: user_id
      # 참고: SSO_AUTO_CREATE_USERS는 False로 고정 (v1.20.0-sso.24+)
```

### 2단계: SSO 백엔드(누비슨 콘솔) 쿠키 설정

**JWT 토큰 발급 시 쿠키 설정 수정**:

```javascript
// Node.js/Express 예시
app.get('/api/sso/token', async (req, res) => {
  // Label Studio에서 JWT 토큰 발급
  const tokenData = await issueJWT(userEmail);

  // 쿠키 설정 (HTTPS 환경)
  res.cookie('ls_auth_token', tokenData.token, {
    domain: '.nubison.io',    // ⭐ 중요: 서브도메인 공유
    path: '/',
    secure: true,              // ⭐ 중요: HTTPS 필수
    httpOnly: false,           // JavaScript 접근 가능
    sameSite: 'lax',           // CSRF 보호
    maxAge: 600 * 1000,        // 10분
  });

  res.json({ success: true });
});
```

```python
# Python/Django 예시
from django.http import JsonResponse

def issue_sso_token(request):
    # JWT 토큰 발급
    token = generate_jwt_token(user)

    response = JsonResponse({'success': True})

    # 쿠키 설정 (HTTPS 환경)
    response.set_cookie(
        key='ls_auth_token',
        value=token,
        domain='.nubison.io',   # ⭐ 중요: 서브도메인 공유
        path='/',
        secure=True,             # ⭐ 중요: HTTPS 필수
        httponly=False,          # JavaScript 접근 가능
        samesite='Lax',          # CSRF 보호
        max_age=600,             # 10분
    )

    return response
```

### 3단계: 컨테이너 재시작

```bash
# docker-compose 사용 시
docker-compose down
docker-compose up -d

# 또는 특정 서비스만 재시작
docker-compose restart labelstudio
```

---

## 설정 예시

### 개발 서버 (console-dev.nubison.io)

```yaml
# docker-compose.yml
version: '3.8'

services:
  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.36
    container_name: label-studio-app
    restart: unless-stopped

    environment:
      # HTTPS 환경 설정
      SESSION_COOKIE_SECURE: true
      CSRF_COOKIE_SECURE: true
      SESSION_COOKIE_DOMAIN: .nubison.io
      CSRF_COOKIE_DOMAIN: .nubison.io
      LABEL_STUDIO_HOST: https://label-dev.nubison.io

      # iframe 허용
      CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io"

      # 데이터베이스
      DJANGO_DB: default
      POSTGRES_HOST: postgres
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

      # SSO 설정
      JWT_SSO_COOKIE_NAME: ls_auth_token
      JWT_SSO_NATIVE_USER_ID_CLAIM: user_id
      # 참고: SSO_AUTO_CREATE_USERS는 False로 고정 (v1.20.0-sso.24+)

      # 로그 레벨
      LOG_LEVEL: INFO
      DEBUG: false

    ports:
      - "8080:8080"

    volumes:
      - labelstudio_data:/label-studio/data

    networks:
      - labelstudio

  postgres:
    image: postgres:13.18
    container_name: label-studio-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: labelstudio
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - labelstudio

volumes:
  labelstudio_data:
  postgres_data:

networks:
  labelstudio:
    driver: bridge
```

### 프로덕션 서버 (console.nubison.io)

```yaml
# 개발 서버와 동일하되, URL만 변경
environment:
  LABEL_STUDIO_HOST: https://label.nubison.io
  CSP_FRAME_ANCESTORS: "'self' https://console.nubison.io"
```

---

## 검증 방법

### 1단계: 브라우저 개발자 도구로 쿠키 확인

1. **누비슨 콘솔 로그인**
   - `https://console-dev.nubison.io` 접속 및 로그인

2. **개발자 도구 열기** (F12 또는 Cmd/Ctrl+Shift+I)

3. **Application 탭 → Cookies → .nubison.io**

4. **ls_auth_token 쿠키 확인**:
   ```
   Name:     ls_auth_token
   Value:    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InRlc3RAbm...
   Domain:   .nubison.io                    ✅ 점(.)으로 시작
   Path:     /                              ✅
   Secure:   ✓                              ✅ 체크되어 있어야 함
   HttpOnly: (비어있음)                      ✅
   SameSite: Lax                            ✅
   ```

5. **Secure 플래그가 없으면?**
   ```
   Secure: (비어있음)  ❌ 문제 발견!

   → SSO 백엔드의 쿠키 설정 확인 필요
   → secure: true 가 설정되어 있는지 확인
   ```

### 2단계: Network 탭으로 요청 확인

1. **Network 탭 열기**

2. **Label Studio 접근**
   - `https://label-dev.nubison.io` 접속

3. **요청 헤더 확인**:
   ```
   Request URL: https://label-dev.nubison.io/
   Request Headers:
     Cookie: ls_auth_token=eyJhbGc...        ✅ 토큰이 전송되어야 함
   ```

4. **쿠키가 전송되지 않으면?**
   ```
   Request Headers:
     Cookie: (없음)                          ❌ 문제 발견!

   → Secure 플래그가 없거나
   → Domain 설정이 잘못되었을 가능성
   ```

### 3단계: Label Studio 로그 확인

```bash
# 로그 실시간 모니터링
docker logs -f label-studio-app

# JWT 관련 로그 필터링
docker logs label-studio-app | grep -i jwt
```

**정상 동작 시 로그**:
```
[JWTAutoLoginMiddleware] JWT token found in cookie
[JWTAutoLoginMiddleware] Token payload: {'user_id': 1, 'email': 'test@example.com', ...}
[JWTAutoLoginMiddleware] User authenticated: test@example.com
```

**비정상 동작 시 로그**:
```
[JWTAutoLoginMiddleware] No JWT token found in cookie      ❌ 쿠키가 전송되지 않음
[JWTAutoLoginMiddleware] Invalid token signature           ❌ SECRET_KEY 불일치
[JWTAutoLoginMiddleware] Token expired                     ❌ 토큰 만료
[JWTAutoLoginMiddleware] User not found: user_id=999       ❌ 사용자가 Label Studio에 없음
```

### 4단계: curl로 직접 테스트

```bash
# 1. JWT 토큰 발급 (SSO 백엔드에서)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InRlc3RAbm..."

# 2. Label Studio 접근 (쿠키 포함)
curl -v \
  -H "Cookie: ls_auth_token=$TOKEN" \
  https://label-dev.nubison.io/

# 3. 응답 확인
# - 200 OK + HTML: 정상 로그인됨
# - 302 Redirect to /user/login/: 인증 실패
```

---

## 트러블슈팅

### 문제 1: 쿠키에 Secure 플래그가 없음

**증상**:
- 브라우저 개발자 도구에서 `ls_auth_token` 쿠키의 Secure 체크박스가 비어있음

**원인**:
- SSO 백엔드에서 쿠키 설정 시 `secure: true` 누락

**해결**:
```javascript
// ❌ 잘못된 예
res.cookie('ls_auth_token', token, {
  domain: '.nubison.io',
  // secure 속성 없음
});

// ✅ 올바른 예
res.cookie('ls_auth_token', token, {
  domain: '.nubison.io',
  secure: true,  // ⭐ 추가
});
```

### 문제 2: 쿠키 도메인이 잘못됨

**증상**:
- 쿠키가 특정 서브도메인에만 저장됨
- 다른 서브도메인에서 쿠키가 보이지 않음

**원인**:
- 도메인 설정이 `.nubison.io`가 아닌 `label-dev.nubison.io`로 되어 있음

**해결**:
```javascript
// ❌ 잘못된 예
res.cookie('ls_auth_token', token, {
  domain: 'label-dev.nubison.io',  // 특정 서브도메인
});

// ✅ 올바른 예
res.cookie('ls_auth_token', token, {
  domain: '.nubison.io',  // ⭐ 점(.)으로 시작 (모든 서브도메인 공유)
});
```

### 문제 3: Label Studio 환경변수 미설정

**증상**:
- 쿠키는 올바르게 설정되었지만 Label Studio에서 인증 실패
- `ls_sessionid` 쿠키가 생성되지 않음

**원인**:
- Label Studio 컨테이너의 `SESSION_COOKIE_SECURE` 환경변수 미설정

**해결**:
```bash
# 환경변수 확인
docker exec label-studio-app env | grep COOKIE_SECURE

# 출력이 없거나 false면 문제
# docker-compose.yml에 추가:
environment:
  SESSION_COOKIE_SECURE: true
  CSRF_COOKIE_SECURE: true
```

### 문제 4: iframe에서만 로그인 실패

**증상**:
- Label Studio에 직접 접근하면 로그인됨
- iframe에서 접근하면 로그인 안 됨

**원인**:
- CSP (Content Security Policy) 설정으로 iframe 차단

**해결**:
```yaml
environment:
  CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io"
```

### 문제 5: 로컬에서는 되는데 서버에서 안 됨

**증상**:
- 로컬 개발 환경 (HTTP)에서는 정상
- 서버 환경 (HTTPS)에서 실패

**원인**:
- HTTP/HTTPS 환경 차이

**해결**:
```yaml
# 로컬 개발 (HTTP)
environment:
  SESSION_COOKIE_SECURE: false
  LABEL_STUDIO_HOST: http://label.nubison.localhost:8080

# 서버 (HTTPS)
environment:
  SESSION_COOKIE_SECURE: true
  LABEL_STUDIO_HOST: https://label-dev.nubison.io
```

### 문제 6: SECRET_KEY 불일치

**증상**:
- Label Studio 로그에 "Invalid token signature" 에러

**원인**:
- SSO 백엔드와 Label Studio의 `SECRET_KEY`가 다름

**해결**:
```bash
# 1. Label Studio의 SECRET_KEY 확인
docker exec label-studio-app cat /label-studio/data/.secret_key

# 2. SSO 백엔드에 동일한 SECRET_KEY 설정
# (또는 Label Studio에서 SSO 백엔드의 SECRET_KEY 사용)
```

---

## 체크리스트

배포 전 필수 확인 사항:

### Label Studio 설정
- [ ] `SESSION_COOKIE_SECURE: true` 설정
- [ ] `CSRF_COOKIE_SECURE: true` 설정
- [ ] `SESSION_COOKIE_DOMAIN: .your-domain.com` 설정
- [ ] `LABEL_STUDIO_HOST: https://label.your-domain.com` 설정
- [ ] `CSP_FRAME_ANCESTORS` 설정 (iframe 사용 시)

### SSO 백엔드 설정
- [ ] JWT 쿠키 `domain: '.your-domain.com'` 설정
- [ ] JWT 쿠키 `secure: true` 설정
- [ ] JWT 쿠키 `sameSite: 'lax'` 설정
- [ ] SECRET_KEY 일치 확인

### 검증
- [ ] 브라우저 개발자 도구에서 쿠키 Secure 플래그 확인
- [ ] Network 탭에서 Cookie 헤더 전송 확인
- [ ] Label Studio 로그에서 JWT 인증 성공 확인
- [ ] iframe에서 정상 동작 확인

---

## 참고 자료

### 관련 문서
- [NUBISON_INTEGRATION_GUIDE.md](./NUBISON_INTEGRATION_GUIDE.md) - iframe 통합 가이드
- [CUSTOM_SSO_TOKEN_API.md](./CUSTOM_SSO_TOKEN_API.md) - Custom SSO Token API 가이드
- [README.md](../README.md) - 전체 프로젝트 가이드

### 외부 링크
- [MDN: Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie)
- [MDN: SameSite cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
- [Django: Session Cookie Settings](https://docs.djangoproject.com/en/5.1/ref/settings/#session-cookie-secure)

---

## 지원

문제가 계속 발생하는 경우:

1. **로그 수집**:
   ```bash
   # Label Studio 로그
   docker logs label-studio-app > label-studio.log

   # SSO 백엔드 로그
   # (누비슨 콘솔 로그)
   ```

2. **브라우저 정보 수집**:
   - 개발자 도구 → Application → Cookies 스크린샷
   - 개발자 도구 → Network → 요청/응답 헤더 스크린샷

3. **GitHub Issues 또는 이메일로 문의**:
   - 로그 파일 첨부
   - 브라우저 정보 (Chrome, Firefox, Safari 등)
   - 환경 정보 (OS, Docker 버전 등)

---

**마지막 업데이트**: 2025-11-07
**버전**: v1.20.0-sso.36
