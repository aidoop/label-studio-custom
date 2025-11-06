# 누비슨 시스템 연동 가이드

## 개요

이 문서는 누비슨 시스템과 Label Studio Custom의 연동 방법을 설명합니다.

---

## 핵심 개념

### 이메일 포맷

누비슨 시스템에서는 한 사용자가 여러 서비스에서 같은 이메일을 사용할 수 있지만, Label Studio는 이메일이 unique해야 합니다.

**해결 방법**: 서비스 ID와 이메일을 조합한 포맷 사용

```
포맷: {서비스ID}_{실제이메일}

예시:
- 누비슨 서비스 s111의 gdh@gmail.com → s111_gdh@gmail.com
- 누비슨 서비스 s222의 gdh@gmail.com → s222_gdh@gmail.com
```

---

## 연동 시나리오

### 1. 회원 생성

```javascript
// 누비슨 시스템
const serviceId = "s111";
const userEmail = "gdh@gmail.com";
const userName = "홍길동";

// ✅ 이메일 포맷팅
const labelStudioEmail = `${serviceId}_${userEmail}`;  // "s111_gdh@gmail.com"

// Label Studio User 생성
POST https://label-studio.example.com/api/users/
Authorization: Token {admin_api_token}
Content-Type: application/json

{
  "email": "s111_gdh@gmail.com",      // ← 포맷된 이메일
  "username": "홍길동",                // ← 실제 사용자 이름
  "first_name": "길동",
  "last_name": "홍",
  "password": "자동생성된비밀번호"
}

Response:
{
  "id": 123,
  "email": "s111_gdh@gmail.com",
  "username": "홍길동",
  ...
}
```

### 2. JWT 토큰 발급 (SSO 로그인)

```javascript
// 누비슨 시스템
const serviceId = "s111";
const userEmail = "gdh@gmail.com";

// ✅ 이메일 포맷팅
const labelStudioEmail = `${serviceId}_${userEmail}`;

// SSO Backend API 호출
GET https://sso-backend.example.com/api/sso/token?email=s111_gdh@gmail.com
```

**SSO Backend (Express.js)**:
```javascript
app.get("/api/sso/token", async (req, res) => {
  // ✅ 이미 포맷된 이메일 받음
  const labelStudioEmail = req.query.email;  // "s111_gdh@gmail.com"

  // Label Studio SSO API 호출
  const response = await fetch(`${LABEL_STUDIO_URL}/api/sso/token`, {
    method: "POST",
    headers: {
      Authorization: `Token ${LABEL_STUDIO_API_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email: labelStudioEmail }),
  });

  const tokenData = await response.json();
  // { token: "eyJ...", expires_in: 600 }

  // JWT 토큰을 쿠키에 설정
  res.cookie("ls_auth_token", tokenData.token, {
    domain: ".example.com",      // 서브도메인 공유
    path: "/",
    secure: true,                // ⚠️ HTTPS 환경에서 필수!
    httpOnly: false,             // iframe에서 접근 가능하도록
    sameSite: "lax",             // CSRF 보호
    maxAge: tokenData.expires_in * 1000,
  });

  res.json(tokenData);
});
```

**⚠️ 중요 - 쿠키 설정 주의사항:**

| 속성 | 값 | 설명 |
|------|-----|------|
| `domain` | `.example.com` | 점(.)으로 시작하여 서브도메인 간 공유 가능 |
| `secure` | `true` | **HTTPS 환경에서 필수!** HTTP 로컬 개발 시에만 `false` |
| `httpOnly` | `false` | iframe에서 쿠키 접근 가능하도록 설정 |
| `sameSite` | `lax` | CSRF 보호, iframe 접근 허용 |

**환경별 설정:**
```javascript
// HTTP 로컬 개발 환경
res.cookie("ls_auth_token", token, {
  domain: ".localhost",
  secure: false,    // HTTP는 false
  // ...
});

// HTTPS 개발/프로덕션 환경
res.cookie("ls_auth_token", token, {
  domain: ".example.com",
  secure: true,     // HTTPS는 true (필수!)
  // ...
});
```

### 2-1. Custom SSO Token Validation API 사용 (권장)

**v1.20.0-sso.22부터 추가**: 사용자 존재 여부를 먼저 검증한 후 JWT 토큰을 발급하는 API

**언제 사용해야 하나요?**

| 시나리오 | 기본 SSO API (`/api/sso/token`) | Custom SSO API (`/api/custom/sso/token`) |
|---------|--------------------------------|------------------------------------------|
| 폐쇄형 시스템 (사전 등록 필수) | ❌ 자동 계정 생성되어 부적합 | ✅ 사용자 없으면 404 오류 반환 |
| 개방형 시스템 (누구나 접근) | ✅ 자동 계정 생성으로 편리 | ❌ 필요 없음 |
| 에러 핸들링 필요 | ❌ 성공만 반환 | ✅ 명확한 에러 코드 제공 |
| 배치 처리 필요 | ❌ 없음 | ✅ Batch API 제공 |

**사용 예시 (권장 방식)**:

```javascript
// 누비슨 Backend API
app.get("/api/sso/token", async (req, res) => {
  const labelStudioEmail = req.query.email;  // "s111_gdh@gmail.com"

  try {
    // ✅ Custom SSO Token Validation API 사용
    const response = await fetch(`${LABEL_STUDIO_URL}/api/custom/sso/token`, {
      method: "POST",
      headers: {
        Authorization: `Token ${LABEL_STUDIO_ADMIN_TOKEN}`,  // ← Admin 토큰 필요
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email: labelStudioEmail }),
    });

    if (!response.ok) {
      const error = await response.json();

      // ✅ 명확한 에러 코드로 처리 가능
      if (error.error_code === 'USER_NOT_FOUND') {
        return res.status(404).json({
          error: "Label Studio 계정이 없습니다. 관리자에게 문의하세요.",
        });
      } else if (error.error_code === 'USER_INACTIVE') {
        return res.status(403).json({
          error: "계정이 비활성 상태입니다. 관리자에게 문의하세요.",
        });
      }

      throw new Error(`Token generation failed: ${error.error}`);
    }

    const tokenData = await response.json();
    // { token: "eyJ...", expires_in: 600, user: {...} }

    // JWT 토큰을 쿠키에 설정
    res.cookie("ls_auth_token", tokenData.token, {
      domain: ".example.com",
      path: "/",
      secure: true,
      httpOnly: false,
      sameSite: "lax",
      maxAge: tokenData.expires_in * 1000,
    });

    res.json(tokenData);

  } catch (error) {
    console.error("SSO token error:", error);
    res.status(500).json({ error: "토큰 발급 실패" });
  }
});
```

**배치 토큰 발급 (여러 사용자 동시 처리)**:

```javascript
// 여러 사용자에게 일괄 토큰 발급
app.post("/api/sso/batch-token", async (req, res) => {
  const { emails } = req.body;  // ["s111_user1@gmail.com", "s111_user2@gmail.com"]

  const response = await fetch(`${LABEL_STUDIO_URL}/api/custom/sso/batch-token`, {
    method: "POST",
    headers: {
      Authorization: `Token ${LABEL_STUDIO_ADMIN_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ emails }),
  });

  const result = await response.json();
  /*
  {
    "total": 2,
    "success": 1,
    "failed": 1,
    "results": {
      "success": [
        { "email": "s111_user1@gmail.com", "token": "...", "user": {...} }
      ],
      "failed": [
        { "email": "s111_user2@gmail.com", "error": "User not found", "error_code": "USER_NOT_FOUND" }
      ]
    }
  }
  */

  res.json(result);
});
```

**자세한 문서**: [Custom SSO Token API Guide](./CUSTOM_SSO_TOKEN_API.md)

### 3. 이메일 변경

```javascript
// 누비슨 시스템에서 이메일 변경
const serviceId = "s111";
const userId = 123;  // Label Studio user_id
const oldEmail = "gdh@gmail.com";
const newEmail = "kim@naver.com";

// ✅ 새 이메일 포맷팅
const newLabelStudioEmail = `${serviceId}_${newEmail}`;  // "s111_kim@naver.com"

// Label Studio User 업데이트
PATCH https://label-studio.example.com/api/users/123/
Authorization: Token {admin_api_token}
Content-Type: application/json

{
  "email": "s111_kim@naver.com"  // ← 포맷된 새 이메일
}

Response:
{
  "id": 123,
  "email": "s111_kim@naver.com",  // ← 이메일 변경됨
  "username": "홍길동",
  ...
}
```

**중요**: 이메일이 변경되어도 `user_id`는 그대로이므로, 기존 JWT 토큰으로 계속 인증 가능합니다.

---

## Helper 함수 (누비슨 시스템)

### JavaScript/TypeScript

```javascript
/**
 * Label Studio용 이메일 포맷
 * @param {string} serviceId - 누비슨 서비스 ID (예: "s111")
 * @param {string} email - 실제 이메일 (예: "gdh@gmail.com")
 * @returns {string} 포맷된 이메일 (예: "s111_gdh@gmail.com")
 */
function formatLabelStudioEmail(serviceId, email) {
  if (!serviceId || !email) {
    throw new Error('serviceId and email are required');
  }
  return `${serviceId}_${email}`;
}

/**
 * 포맷된 이메일에서 정보 추출
 * @param {string} formattedEmail - 포맷된 이메일 (예: "s111_gdh@gmail.com")
 * @returns {object} { serviceId: "s111", email: "gdh@gmail.com" }
 */
function parseLabelStudioEmail(formattedEmail) {
  if (!formattedEmail || !formattedEmail.includes('_')) {
    throw new Error('Invalid formatted email');
  }

  const firstUnderscoreIndex = formattedEmail.indexOf('_');
  const serviceId = formattedEmail.substring(0, firstUnderscoreIndex);
  const email = formattedEmail.substring(firstUnderscoreIndex + 1);

  return { serviceId, email };
}

// 사용 예시
const formatted = formatLabelStudioEmail("s111", "gdh@gmail.com");
console.log(formatted);  // "s111_gdh@gmail.com"

const parsed = parseLabelStudioEmail("s111_gdh@gmail.com");
console.log(parsed);  // { serviceId: "s111", email: "gdh@gmail.com" }
```

### Python

```python
def format_label_studio_email(service_id: str, email: str) -> str:
    """
    Label Studio용 이메일 포맷

    Args:
        service_id: 누비슨 서비스 ID (예: "s111")
        email: 실제 이메일 (예: "gdh@gmail.com")

    Returns:
        포맷된 이메일 (예: "s111_gdh@gmail.com")
    """
    if not service_id or not email:
        raise ValueError("service_id and email are required")
    return f"{service_id}_{email}"


def parse_label_studio_email(formatted_email: str) -> dict:
    """
    포맷된 이메일에서 정보 추출

    Args:
        formatted_email: 포맷된 이메일 (예: "s111_gdh@gmail.com")

    Returns:
        dict: {"service_id": "s111", "email": "gdh@gmail.com"}
    """
    if not formatted_email or '_' not in formatted_email:
        raise ValueError("Invalid formatted email")

    service_id, email = formatted_email.split('_', 1)
    return {"service_id": service_id, "email": email}


# 사용 예시
formatted = format_label_studio_email("s111", "gdh@gmail.com")
print(formatted)  # "s111_gdh@gmail.com"

parsed = parse_label_studio_email("s111_gdh@gmail.com")
print(parsed)  # {"service_id": "s111", "email": "gdh@gmail.com"}
```

---

## API 엔드포인트

### 1. User 조회 (이메일로)

```http
GET /api/users/by-email/?email={formatted_email}
Authorization: Token {admin_api_token}
```

**Response:**
```json
{
  "id": 123,
  "email": "s111_gdh@gmail.com",
  "username": "홍길동",
  "first_name": "길동",
  "last_name": "홍"
}
```

**Use case**: JWT 토큰 발급 전에 user_id 확인

---

### 2. User 업데이트 (이메일 수정)

```http
PATCH /api/users/{user_id}/
Authorization: Token {admin_api_token}
Content-Type: application/json

{
  "email": "s111_new@email.com",
  "first_name": "Updated Name"
}
```

**Response:**
```json
{
  "id": 123,
  "email": "s111_new@email.com",
  "username": "홍길동",
  "first_name": "Updated Name",
  "last_name": "홍"
}
```

**권한:**
- Admin: 모든 사용자 업데이트 가능
- 일반 사용자: 자신만 업데이트 가능

---

## 주의사항

### 1. 이메일 unique 제약

포맷된 이메일도 Label Studio 전체에서 unique해야 합니다.

```javascript
// ❌ 오류 발생
formatLabelStudioEmail("s111", "gdh@gmail.com");  // "s111_gdh@gmail.com"
formatLabelStudioEmail("s111", "gdh@gmail.com");  // 중복! 오류 발생

// ✅ 정상
formatLabelStudioEmail("s111", "gdh@gmail.com");  // "s111_gdh@gmail.com"
formatLabelStudioEmail("s222", "gdh@gmail.com");  // "s222_gdh@gmail.com" (다른 서비스)
```

### 2. JWT 토큰은 user_id 기반

이메일이 변경되어도 JWT 인증은 `user_id`를 사용하므로 문제없습니다.

```python
# JWT payload
{
  "user_id": 123,  # ← 이것으로 인증
  "email": "s111_gdh@gmail.com",  # 참고용
  "exp": 1234567890
}

# 이메일 변경 후에도
user = User.objects.get(pk=123)  # ← user_id로 검색하므로 정상 작동
```

### 3. username 필드 활용

`username` 필드는 unique 제약이 없으므로, 실제 사용자 이름을 저장하는데 사용할 수 있습니다.

```javascript
// 회원 생성 시
{
  "email": "s111_gdh@gmail.com",     // 고유 식별자
  "username": "홍길동",               // 실제 이름 (중복 가능)
  "first_name": "길동",
  "last_name": "홍"
}
```

---

## 문제 해결

### Q1: 이메일이 너무 길어서 문제가 될까요?

A: Label Studio의 email 필드는 최대 254자이므로, 일반적인 서비스 ID와 이메일 조합은 문제없습니다.

```python
# users/models.py
email = models.EmailField(_('email address'), unique=True, blank=True)
# EmailField 기본 max_length = 254
```

### Q2: 기존 사용자는 어떻게 마이그레이션하나요?

A: 기존 이메일에 서비스 ID를 추가하여 업데이트합니다.

```javascript
// 기존 사용자
email: "gdh@gmail.com"

// 마이그레이션
PATCH /api/users/123/
{
  "email": "s111_gdh@gmail.com"
}
```

### Q3: Organization은 어떻게 활용하나요?

A: Organization을 누비슨 서비스 단위로 사용할 수 있습니다.

```javascript
// 서비스별 Organization 생성
Organization 1: "누비슨 서비스 s111"
Organization 2: "누비슨 서비스 s222"

// 사용자는 Organization별로 다른 계정 보유
User 1 (Org 1): s111_gdh@gmail.com
User 2 (Org 2): s222_gdh@gmail.com
```

---

## iframe 통합

### 1. iframe으로 Label Studio 임베딩

누비슨 콘솔에서 Label Studio를 iframe으로 임베딩할 때 `hideHeader=true` 파라미터를 사용하세요.

```html
<!-- 누비슨 콘솔 (Vue 3) -->
<template>
  <div class="labelstudio-container">
    <iframe
      :src="labelStudioUrl"
      frameborder="0"
      style="width: 100%; height: 100vh;"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';

const projectId = 123;

// ✅ hideHeader=true 파라미터 추가
const labelStudioUrl = computed(() =>
  `https://labelstudio.example.com/projects/${projectId}?hideHeader=true`
);
</script>
```

**hideHeader 파라미터의 역할:**
1. ✅ Label Studio 헤더 완전 제거 (전체 화면 활용)
2. ✅ iframe 환경 감지 (로그인 실패 시 SSO 안내 페이지 표시)

### 2. 인증 오류 처리 (postMessage)

iframe에서 인증 오류 발생 시 부모 창으로 메시지가 전달됩니다.

```javascript
// 누비슨 콘솔 (부모 창)
window.addEventListener('message', (event) => {
  if (event.data.type === 'LABEL_STUDIO_AUTH_ERROR') {
    console.log('Label Studio 인증 오류:', event.data);
    // {
    //   type: 'LABEL_STUDIO_AUTH_ERROR',
    //   error: 'UNAUTHORIZED_ACCESS',
    //   message: 'SSO authentication required'
    // }

    // 처리 방법 1: iframe 숨기고 재인증 유도
    document.getElementById('labelstudio-iframe').style.display = 'none';
    showReauthenticationDialog();

    // 처리 방법 2: 자동으로 토큰 재발급 시도
    refreshSSOToken().then((newToken) => {
      // 새 토큰으로 iframe 리로드
      location.reload();
    });
  }
});
```

### 3. iframe 통합 전체 예시

```vue
<!-- 누비슨 콘솔 - LabelStudioIframe.vue -->
<template>
  <div class="labelstudio-wrapper">
    <!-- 로딩 상태 -->
    <div v-if="loading" class="loading">
      <p>Label Studio 로딩 중...</p>
    </div>

    <!-- 인증 오류 -->
    <div v-else-if="authError" class="error">
      <p>인증이 만료되었습니다.</p>
      <button @click="handleReauth">다시 로그인</button>
    </div>

    <!-- Label Studio iframe -->
    <iframe
      v-else
      :src="labelStudioUrl"
      frameborder="0"
      class="labelstudio-iframe"
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useLabelStudioSSO } from '@/composables/useLabelStudioSSO';

const props = defineProps({
  projectId: { type: Number, required: true },
});

const loading = ref(true);
const authError = ref(false);
const { generateSSOToken } = useLabelStudioSSO();

// Label Studio URL (hideHeader=true)
const labelStudioUrl = computed(() =>
  `https://labelstudio.example.com/projects/${props.projectId}?hideHeader=true`
);

// iframe 로드 완료
function onIframeLoad() {
  loading.value = false;
}

// 재인증 처리
async function handleReauth() {
  loading.value = true;
  authError.value = false;

  try {
    await generateSSOToken();
    location.reload();
  } catch (error) {
    console.error('재인증 실패:', error);
  }
}

// postMessage 리스너
function handleMessage(event) {
  if (event.data.type === 'LABEL_STUDIO_AUTH_ERROR') {
    loading.value = false;
    authError.value = true;
  }
}

onMounted(() => {
  window.addEventListener('message', handleMessage);
});

onUnmounted(() => {
  window.removeEventListener('message', handleMessage);
});
</script>

<style scoped>
.labelstudio-wrapper {
  width: 100%;
  height: 100vh;
  position: relative;
}

.labelstudio-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.loading, .error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
```

### 4. CSP (Content-Security-Policy) 설정

iframe 임베딩을 위해 Label Studio의 CSP 설정이 필요합니다.

**Label Studio 환경변수:**
```yaml
environment:
  # 누비슨 콘솔 도메인 허용
  CSP_FRAME_ANCESTORS: "'self' https://console-dev.nubison.io https://console.nubison.io"
```

**자세한 문서**: [DEPLOYMENT.md - iframe 임베딩 보안 헤더 설정](../DEPLOYMENT.md#iframe-임베딩-보안-헤더-설정)

---

## 참고 자료

- [Label Studio SSO 가이드](https://labelstud.io/guide/auth_setup.html)
- [Label Studio API 문서](https://labelstud.io/api)
- [label-studio-sso 패키지](https://pypi.org/project/label-studio-sso/)
- [Custom SSO Token API Guide](./CUSTOM_SSO_TOKEN_API.md)
