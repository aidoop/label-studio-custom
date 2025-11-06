# Custom SSO Token Validation API

## 개요

이 문서는 label-studio-custom의 **Custom SSO Token Validation API**에 대한 가이드입니다.

### 왜 필요한가?

기본 SSO Token API (`/api/sso/token`)는 `SSO_AUTO_CREATE_USERS=true` 설정 시, 존재하지 않는 사용자에 대해서도 JWT 토큰을 발급하고 자동으로 계정을 생성합니다. 이는 일부 시나리오에서는 바람직하지 않을 수 있습니다:

- **문제 1**: 존재하지 않는 사용자에게도 토큰이 발급됨
- **문제 2**: 사용자가 실제로 존재하는지 확인 후 토큰 발급이 필요한 경우

**Custom SSO Token Validation API**는 다음을 제공합니다:

1. ✅ **사전 검증**: 사용자 존재 여부를 먼저 확인
2. ✅ **명확한 에러 코드**: `USER_NOT_FOUND`, `USER_INACTIVE` 등 상세한 오류 반환
3. ✅ **배치 처리**: 여러 사용자에 대한 토큰을 한 번에 발급
4. ✅ **관리자 전용**: `IsAdminUser` 권한으로 보안 강화

---

## API 엔드포인트

### 1. Single Token Validation API

**Endpoint**: `POST /api/custom/sso/token`

단일 사용자에 대해 존재 여부를 검증한 후 JWT 토큰을 발급합니다.

#### Request

```http
POST /api/custom/sso/token
Content-Type: application/json
Authorization: Token <admin_token>

{
  "email": "user@example.com"
}
```

**Parameters**:
- `email` (required): 사용자 이메일 주소

**Authentication**:
- `IsAdminUser` 권한 필요 (superuser 계정 필요)

#### Success Response (200 OK)

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 600,
  "user": {
    "id": 123,
    "email": "user@example.com",
    "username": "user",
    "is_superuser": false
  }
}
```

#### Error Responses

**400 Bad Request** - email 파라미터 누락:
```json
{
  "success": false,
  "error": "email is required",
  "error_code": "INVALID_REQUEST"
}
```

**401 Unauthorized** - 인증 토큰 없음:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden** - Admin 권한 없음:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**403 Forbidden** - 비활성 사용자:
```json
{
  "success": false,
  "error": "User is inactive: user@example.com",
  "error_code": "USER_INACTIVE",
  "email": "user@example.com"
}
```

**404 Not Found** - 사용자 없음:
```json
{
  "success": false,
  "error": "User not found: user@example.com",
  "error_code": "USER_NOT_FOUND",
  "email": "user@example.com"
}
```

---

### 2. Batch Token Validation API

**Endpoint**: `POST /api/custom/sso/batch-token`

여러 사용자에 대해 한 번에 토큰을 발급합니다. 일부 실패해도 성공한 사용자들의 토큰은 반환됩니다.

#### Request

```http
POST /api/custom/sso/batch-token
Content-Type: application/json
Authorization: Token <admin_token>

{
  "emails": [
    "user1@example.com",
    "user2@example.com",
    "user3@example.com"
  ]
}
```

**Parameters**:
- `emails` (required): 이메일 주소 배열 (list of strings)

**Authentication**:
- `IsAdminUser` 권한 필요

#### Success Response (200 OK)

```json
{
  "total": 3,
  "success": 2,
  "failed": 1,
  "results": {
    "success": [
      {
        "email": "user1@example.com",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 600,
        "user": {
          "id": 123,
          "email": "user1@example.com",
          "username": "user1",
          "is_superuser": false
        }
      },
      {
        "email": "user2@example.com",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 600,
        "user": {
          "id": 124,
          "email": "user2@example.com",
          "username": "user2",
          "is_superuser": false
        }
      }
    ],
    "failed": [
      {
        "email": "user3@example.com",
        "error": "User not found: user3@example.com",
        "error_code": "USER_NOT_FOUND"
      }
    ]
  }
}
```

**Response 구조**:
- `total`: 요청한 전체 이메일 수
- `success`: 성공한 토큰 발급 수
- `failed`: 실패한 토큰 발급 수
- `results.success`: 성공한 사용자들의 토큰 정보 배열
- `results.failed`: 실패한 사용자들의 오류 정보 배열

#### Error Responses

**400 Bad Request** - emails 파라미터 오류:
```json
{
  "success": false,
  "error": "emails parameter is required and must be a non-empty list",
  "error_code": "INVALID_REQUEST"
}
```

**401 Unauthorized** / **403 Forbidden**: Single API와 동일

---

## 사용 예시

### Node.js / Express Backend

#### 1. Single Token 발급

```javascript
const axios = require('axios');

async function getValidatedSSOToken(userEmail) {
  try {
    const response = await axios.post(
      'https://labelstudio.example.com/api/custom/sso/token',
      { email: userEmail },
      {
        headers: {
          'Authorization': `Token ${process.env.LABEL_STUDIO_ADMIN_TOKEN}`,
          'Content-Type': 'application/json',
        },
      }
    );

    const { token, expires_in, user } = response.data;
    console.log(`토큰 발급 성공: ${user.email}`);
    return token;

  } catch (error) {
    if (error.response) {
      const { error_code, error: errorMessage } = error.response.data;

      switch (error_code) {
        case 'USER_NOT_FOUND':
          console.error('사용자 없음:', errorMessage);
          // 사용자에게 가입 필요 안내
          return null;

        case 'USER_INACTIVE':
          console.error('비활성 계정:', errorMessage);
          // 사용자에게 계정 활성화 필요 안내
          return null;

        default:
          console.error('토큰 발급 실패:', errorMessage);
          throw error;
      }
    }
    throw error;
  }
}

// 사용 예시
app.get('/labelstudio/access', async (req, res) => {
  const userEmail = req.user.email;

  const token = await getValidatedSSOToken(userEmail);

  if (!token) {
    return res.status(404).json({
      error: 'Label Studio 계정이 없습니다. 관리자에게 문의하세요.',
    });
  }

  // 쿠키 설정하여 Label Studio로 리다이렉트
  res.cookie('ls_auth_token', token, {
    domain: '.example.com',
    path: '/',
    secure: true,
    httpOnly: false,
    sameSite: 'lax',
    maxAge: 600 * 1000, // 10분
  });

  res.redirect('https://labelstudio.example.com');
});
```

#### 2. Batch Token 발급

```javascript
async function getBatchSSOTokens(userEmails) {
  try {
    const response = await axios.post(
      'https://labelstudio.example.com/api/custom/sso/batch-token',
      { emails: userEmails },
      {
        headers: {
          'Authorization': `Token ${process.env.LABEL_STUDIO_ADMIN_TOKEN}`,
          'Content-Type': 'application/json',
        },
      }
    );

    const { total, success, failed, results } = response.data;

    console.log(`총 ${total}명 중 ${success}명 성공, ${failed}명 실패`);

    // 성공한 사용자들의 토큰 매핑
    const tokenMap = {};
    results.success.forEach((item) => {
      tokenMap[item.email] = item.token;
    });

    // 실패한 사용자들 로깅
    results.failed.forEach((item) => {
      console.error(`${item.email}: ${item.error} (${item.error_code})`);
    });

    return tokenMap;

  } catch (error) {
    console.error('Batch token 발급 실패:', error);
    throw error;
  }
}

// 사용 예시: 여러 사용자에게 일괄 액세스 권한 부여
app.post('/labelstudio/bulk-invite', async (req, res) => {
  const { emails } = req.body;

  const tokenMap = await getBatchSSOTokens(emails);

  // 성공한 사용자들에게 이메일 전송 등
  const successEmails = Object.keys(tokenMap);

  res.json({
    success: successEmails.length,
    failed: emails.length - successEmails.length,
    tokens: tokenMap,
  });
});
```

---

## 기본 SSO API와 비교

| 항목 | 기본 `/api/sso/token` | Custom `/api/custom/sso/token` |
|------|------------------------|--------------------------------|
| **사용자 존재 확인** | ❌ 확인 안 함 (자동 생성) | ✅ 사전 확인 |
| **자동 계정 생성** | ✅ `SSO_AUTO_CREATE_USERS=true` 시 | ❌ 생성 안 함 |
| **사용자 없음 처리** | 200 OK (새 계정 생성) | 404 NOT FOUND |
| **비활성 사용자** | 토큰 발급됨 | 403 FORBIDDEN |
| **에러 코드** | ❌ 없음 | ✅ `USER_NOT_FOUND`, `USER_INACTIVE` |
| **배치 처리** | ❌ 없음 | ✅ Batch API 제공 |
| **권한** | `IsAuthenticated` | `IsAdminUser` |
| **사용 시나리오** | 개방형 SSO (누구나 접근) | 폐쇄형 SSO (사전 등록 필수) |

---

## 마이그레이션 가이드

### 기존 `/api/sso/token` 사용 중인 경우

기존에 `/api/sso/token`을 사용하고 있었다면, 다음과 같이 마이그레이션할 수 있습니다.

#### Before (기본 SSO API)

```javascript
// 모든 사용자에게 자동으로 계정 생성 및 토큰 발급
const response = await axios.post('/api/sso/token', { email });
const token = response.data.token;
```

**문제점**:
- 존재하지 않는 사용자도 자동 생성됨
- 사전 등록하지 않은 사용자도 접근 가능
- 에러 핸들링 어려움

#### After (Custom SSO API)

```javascript
try {
  const response = await axios.post('/api/custom/sso/token', { email });
  const token = response.data.token;

  // 토큰 발급 성공
  return token;

} catch (error) {
  if (error.response?.data?.error_code === 'USER_NOT_FOUND') {
    // 사용자에게 "관리자에게 계정 요청하세요" 안내
    return null;
  }
  throw error;
}
```

**개선점**:
- ✅ 사전 등록된 사용자만 접근 가능
- ✅ 명확한 에러 처리 가능
- ✅ 보안 강화 (폐쇄형 시스템)

---

## 에러 코드 참조

| Error Code | HTTP Status | 설명 | 해결 방법 |
|------------|-------------|------|----------|
| `INVALID_REQUEST` | 400 | email 파라미터 누락 또는 형식 오류 | 올바른 email 파라미터 전달 |
| `USER_NOT_FOUND` | 404 | 사용자가 Label Studio에 존재하지 않음 | 관리자가 사용자 계정 생성 필요 |
| `USER_INACTIVE` | 403 | 사용자 계정이 비활성 상태 | 관리자가 계정 활성화 필요 |

---

## 보안 고려사항

### 1. Admin Token 관리

Custom SSO API는 `IsAdminUser` 권한이 필요하므로, 반드시 **Superuser 계정의 Token**을 사용해야 합니다.

```bash
# Label Studio에서 Admin Token 발급
curl -X POST https://labelstudio.example.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin_password"
  }'
```

발급받은 토큰은 **환경변수**로 안전하게 관리하세요:

```bash
# .env
LABEL_STUDIO_ADMIN_TOKEN=your_admin_token_here
```

### 2. HTTPS 사용 필수

프로덕션 환경에서는 반드시 HTTPS를 사용하여 토큰 탈취를 방지하세요.

### 3. 토큰 만료 시간

SSO 토큰의 기본 만료 시간은 **600초 (10분)**입니다. 환경변수로 조정 가능합니다:

```yaml
environment:
  SSO_TOKEN_EXPIRY: 600  # 초 단위
```

---

## 테스트

### 테스트 실행

```bash
# 모든 SSO Token API 테스트
make test-sso

# Single Token API 테스트만
make test-sso-token

# Batch Token API 테스트만
make test-sso-batch
```

### 수동 테스트

#### 1. Single Token API 테스트

```bash
# 1. Admin Token 발급
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.token')

# 2. 존재하는 사용자 토큰 요청 (200 OK)
curl -X POST http://localhost:8080/api/custom/sso/token \
  -H "Authorization: Token ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com"}' \
  | jq

# 3. 존재하지 않는 사용자 토큰 요청 (404 NOT FOUND)
curl -X POST http://localhost:8080/api/custom/sso/token \
  -H "Authorization: Token ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@test.com"}' \
  | jq
```

#### 2. Batch Token API 테스트

```bash
curl -X POST http://localhost:8080/api/custom/sso/batch-token \
  -H "Authorization: Token ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      "user1@test.com",
      "user2@test.com",
      "nonexistent@test.com"
    ]
  }' \
  | jq
```

---

## FAQ

### Q1: 기존 `/api/sso/token`과 함께 사용 가능한가요?

**A**: 네, 두 API는 독립적으로 동작합니다. 필요에 따라 선택하여 사용할 수 있습니다.

- `/api/sso/token`: 개방형 시스템 (자동 계정 생성)
- `/api/custom/sso/token`: 폐쇄형 시스템 (사전 등록 필수)

### Q2: Batch API에서 일부만 실패하면 어떻게 되나요?

**A**: 일부 실패해도 성공한 사용자들의 토큰은 정상적으로 반환됩니다. `results.success`와 `results.failed`를 각각 확인하세요.

### Q3: 이메일 대소문자를 구분하나요?

**A**: Django User 모델의 기본 동작을 따릅니다. 일반적으로 정확히 일치하는 이메일만 찾습니다.

### Q4: 비활성 사용자는 어떻게 되나요?

**A**: `is_active=False`인 사용자는 `403 USER_INACTIVE` 에러를 반환합니다.

---

## 관련 문서

- [label-studio-sso 패키지](https://github.com/Nubison-Inc/label-studio-sso)
- [누비슨 통합 가이드](./NUBISON_INTEGRATION_GUIDE.md)
- [Custom Export API](./CUSTOM_EXPORT_API.md)

---

## 버전 정보

- **추가된 버전**: v1.20.0-sso.22
- **API 버전**: v1.0
- **Label Studio**: 1.20.0
- **label-studio-sso**: 6.0.7
