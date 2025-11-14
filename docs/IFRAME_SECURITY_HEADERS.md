# iframe 임베딩 보안 헤더 설정 가이드

## 개요

Label Studio Custom은 환경변수를 통해 iframe 임베딩 보안 헤더를 설정할 수 있습니다:
- **Content-Security-Policy** (CSP) - 최신 브라우저 권장
- **X-Frame-Options** - 구형 브라우저 지원

---

## 🎯 Quick Start

### 개발 환경 (특정 도메인만 허용)

```bash
# docker-compose.yml 또는 .env
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io http://localhost:4000
X_FRAME_OPTIONS=SAMEORIGIN
```

### 운영 환경 (프로덕션)

```bash
# docker-compose.yml 또는 .env
CSP_FRAME_ANCESTORS='self' https://console.nubison.io
X_FRAME_OPTIONS=SAMEORIGIN
```

### 모든 도메인 허용 (테스트용, 비권장)

```bash
CSP_FRAME_ANCESTORS=*
```

---

## 📋 환경변수 상세 설명

### 1. Content-Security-Policy (권장)

#### 옵션 A: `CSP_FRAME_ANCESTORS` (간편 모드)

**frame-ancestors 지시문만 설정**하는 간편한 방법입니다.

```bash
# 특정 도메인 허용
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io https://console.nubison.io

# 같은 도메인만 허용
CSP_FRAME_ANCESTORS='self'

# 모든 도메인 허용 (테스트용)
CSP_FRAME_ANCESTORS=*

# iframe 완전 차단
CSP_FRAME_ANCESTORS='none'
```

**생성되는 헤더:**
```http
Content-Security-Policy: frame-ancestors 'self' https://console-dev.nubison.io;
```

#### 옵션 B: `CONTENT_SECURITY_POLICY` (고급 모드)

**전체 CSP 정책**을 직접 설정하는 고급 방법입니다.

```bash
# frame-ancestors와 다른 정책을 함께 설정
CONTENT_SECURITY_POLICY="frame-ancestors 'self' https://console.nubison.io; default-src 'self'; script-src 'self' 'unsafe-inline'"
```

**생성되는 헤더:**
```http
Content-Security-Policy: frame-ancestors 'self' https://console.nubison.io; default-src 'self'; script-src 'self' 'unsafe-inline'
```

---

### 2. X-Frame-Options (폴백용)

구형 브라우저 지원을 위한 설정입니다. CSP가 우선 적용되므로 폴백용으로만 사용됩니다.

```bash
# 같은 도메인만 허용 (가장 일반적)
X_FRAME_OPTIONS=SAMEORIGIN

# iframe 완전 차단
X_FRAME_OPTIONS=DENY

# 특정 도메인 허용 (deprecated, 비권장)
X_FRAME_OPTIONS=ALLOW-FROM https://console.nubison.io
```

**생성되는 헤더:**
```http
X-Frame-Options: SAMEORIGIN
```

---

## 🔍 우선순위 규칙

### 1. 서버(nginx) vs 앱(Label Studio)

**서버에서 설정된 헤더가 우선 적용됩니다.**

```nginx
# nginx 설정 (우선순위 1)
add_header X-Frame-Options "SAMEORIGIN";
add_header Content-Security-Policy "frame-ancestors 'self' https://console.nubison.io";
```

```bash
# Label Studio 환경변수 (우선순위 2 - 서버 설정이 없을 때만 적용)
X_FRAME_OPTIONS=DENY  # ← nginx 설정이 있으면 무시됨
```

**권장**: 서버와 앱 중 **한 곳에서만** 설정하세요.

### 2. CSP vs X-Frame-Options

**최신 브라우저는 CSP를 우선 적용합니다.**

```http
X-Frame-Options: DENY
Content-Security-Policy: frame-ancestors *
```

→ 최신 브라우저는 CSP를 따라 **모든 도메인 허용**

→ 구형 브라우저는 X-Frame-Options를 따라 **완전 차단**

---

## 📊 시나리오별 설정 예시

### 시나리오 1: 누비슨 콘솔에서만 iframe 허용

**요구사항:**
- https://console-dev.nubison.io (개발)
- https://console.nubison.io (운영)
- http://localhost:4000 (로컬 테스트)

```bash
# docker-compose.yml
services:
  labelstudio:
    environment:
      CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io https://console.nubison.io http://localhost:4000"
      X_FRAME_OPTIONS: "SAMEORIGIN"
```

**결과:**
- ✅ 누비슨 콘솔에서 iframe 로드 성공
- ❌ 다른 사이트에서 iframe 로드 차단

---

### 시나리오 2: 개발/운영 환경 분리

**개발 환경:**
```bash
# .env.dev
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io http://localhost:4000
X_FRAME_OPTIONS=SAMEORIGIN
```

**운영 환경:**
```bash
# .env.prod
CSP_FRAME_ANCESTORS='self' https://console.nubison.io
X_FRAME_OPTIONS=SAMEORIGIN
```

---

### 시나리오 3: 테스트 중 (모든 도메인 허용)

```bash
# 테스트용 - 보안 취약하므로 프로덕션에서는 사용 금지!
CSP_FRAME_ANCESTORS=*
```

**경고:** 프로덕션 환경에서는 절대 사용하지 마세요!

---

### 시나리오 4: iframe 완전 차단

```bash
# iframe 사용 안 함
CSP_FRAME_ANCESTORS='none'
X_FRAME_OPTIONS=DENY
```

---

## 🧪 테스트 방법

### 1. 헤더 확인 (브라우저)

```javascript
// 개발자 도구 → Network 탭
// Label Studio 페이지 요청 확인

// Response Headers:
Content-Security-Policy: frame-ancestors 'self' https://console-dev.nubison.io;
X-Frame-Options: SAMEORIGIN
```

### 2. 헤더 확인 (curl)

```bash
curl -I https://label.nubison.io/projects/

# 출력:
# Content-Security-Policy: frame-ancestors 'self' https://console-dev.nubison.io;
# X-Frame-Options: SAMEORIGIN
```

### 3. iframe 임베딩 테스트

```html
<!-- 허용된 도메인 (https://console-dev.nubison.io) -->
<!DOCTYPE html>
<html>
<body>
  <iframe src="https://label.nubison.io/projects/1" width="100%" height="600"></iframe>
  <!-- ✅ 정상 로드 -->
</body>
</html>
```

```html
<!-- 허용되지 않은 도메인 (https://other-site.com) -->
<!DOCTYPE html>
<html>
<body>
  <iframe src="https://label.nubison.io/projects/1" width="100%" height="600"></iframe>
  <!-- ❌ 브라우저 콘솔 오류:
       Refused to display 'https://label.nubison.io/projects/1' in a frame
       because an ancestor violates the following Content Security Policy directive:
       "frame-ancestors 'self' https://console-dev.nubison.io"
  -->
</body>
</html>
```

---

## ⚙️ Docker Compose 설정 예시

### docker-compose.yml

```yaml
version: '3.8'

services:
  labelstudio:
    image: ghcr.io/aidoop/label-studio-custom:1.20.0-sso.36
    environment:
      # iframe 보안 헤더 설정
      CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io https://console.nubison.io"
      X_FRAME_OPTIONS: "SAMEORIGIN"

      # 기타 설정
      DJANGO_DB: default
      POSTGRES_HOST: postgres
      # ...
```

### .env 파일 사용

```bash
# .env
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io
X_FRAME_OPTIONS=SAMEORIGIN
```

```yaml
# docker-compose.yml
services:
  labelstudio:
    env_file:
      - .env
```

---

## 🔧 문제 해결

### Q1: iframe이 로드되지 않아요

**증상:**
```
Refused to display in a frame because it set 'X-Frame-Options' to 'DENY'
```

**해결:**
1. 환경변수 확인:
   ```bash
   docker exec label-studio-app env | grep CSP
   docker exec label-studio-app env | grep X_FRAME
   ```

2. 헤더 확인:
   ```bash
   curl -I https://label.nubison.io/
   ```

3. 서버(nginx) 설정 확인:
   - nginx 설정에서 보안 헤더가 이중으로 설정되어 있는지 확인
   - 서버 설정이 앱 설정을 덮어씀

---

### Q2: CSP를 설정했는데 X-Frame-Options가 적용돼요

**원인:** 구형 브라우저는 CSP를 지원하지 않습니다.

**해결:** 정상 동작입니다. 구형 브라우저 지원을 위해 X-Frame-Options도 함께 설정하세요.

---

### Q3: 여러 도메인을 허용하고 싶어요

**해결:**
```bash
# 공백으로 구분하여 여러 도메인 나열
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io https://console.nubison.io https://admin.nubison.io
```

---

### Q4: http와 https를 모두 허용하고 싶어요

**해결:**
```bash
# 프로토콜을 명시적으로 포함
CSP_FRAME_ANCESTORS='self' http://localhost:4000 https://console-dev.nubison.io
```

**주의:** 프로덕션에서는 https만 사용하세요!

---

### Q5: 포트번호가 다른 같은 도메인 허용

**해결:**
```bash
# 포트번호를 명시적으로 포함
CSP_FRAME_ANCESTORS='self' https://console-dev.nubison.io:4000 https://console-dev.nubison.io
```

---

## 📚 참고 자료

### Content-Security-Policy
- [MDN: Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy)
- [CSP frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors)

### X-Frame-Options
- [MDN: X-Frame-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Frame-Options)

### 브라우저 지원
- CSP frame-ancestors: Chrome 40+, Firefox 33+, Safari 10+, Edge 15+
- X-Frame-Options: 모든 최신 브라우저 지원

---

## 🔒 보안 권장사항

1. **프로덕션에서는 구체적인 도메인 명시**
   ```bash
   # ✅ 좋음
   CSP_FRAME_ANCESTORS='self' https://console.nubison.io

   # ❌ 나쁨
   CSP_FRAME_ANCESTORS=*
   ```

2. **https 사용**
   ```bash
   # ✅ 좋음
   CSP_FRAME_ANCESTORS='self' https://console.nubison.io

   # ❌ 나쁨 (http는 안전하지 않음)
   CSP_FRAME_ANCESTORS='self' http://console.nubison.io
   ```

3. **최소 권한 원칙**
   - 필요한 도메인만 허용
   - 테스트 도메인은 프로덕션에서 제거

4. **정기적인 검토**
   - 사용하지 않는 도메인 제거
   - 보안 정책 업데이트

---

## 📝 변경 이력

### v1.20.0-sso.19 (예정)
- Content-Security-Policy 환경변수 지원 추가
- X-Frame-Options 환경변수 개선
- 커스텀 보안 미들웨어 구현

### 기존 버전
- X-Frame-Options 기본 지원 (ALLOW/DENY/SAMEORIGIN)
