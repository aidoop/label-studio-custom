# Webhook Payload 커스터마이징 가이드

Label Studio Custom의 Webhook payload에는 기본 Label Studio에 없는 사용자 정보가 추가됩니다.

## 기능 개요

### 추가되는 정보

Annotation 이벤트(`ANNOTATION_CREATED`, `ANNOTATION_UPDATED`, `ANNOTATIONS_DELETED`)가 발생할 때, webhook payload에 `completed_by_info` 필드가 자동으로 추가됩니다.

```json
{
  "annotation": {
    "completed_by": 1,
    "completed_by_info": {
      "id": 1,
      "email": "user@example.com",
      "username": "user1",
      "is_superuser": false
    }
  }
}
```

### 포함되는 사용자 정보

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 사용자 ID (completed_by와 동일) |
| `email` | string | 사용자 이메일 주소 |
| `username` | string | 사용자명 |
| `is_superuser` | boolean | 관리자 권한 여부 |

## 사용 예시

### 1. MLOps Webhook Handler 구현

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook/<int:project_id>', methods=['POST'])
def handle_webhook(project_id):
    """
    Label Studio webhook을 수신하여 모델 성능을 계산합니다.
    """
    payload = request.json
    action = payload.get('action')

    print(f"Received {action} event for project {project_id}")

    # Annotation 이벤트만 처리
    if action not in ['ANNOTATION_CREATED', 'ANNOTATION_UPDATED']:
        return jsonify({"status": "ignored", "reason": "not an annotation event"})

    # 사용자 정보 추출
    annotation = payload.get('annotation', {})
    user_info = annotation.get('completed_by_info', {})

    # 사용자 정보가 없는 경우 (이전 버전 호환성)
    if not user_info:
        user_id = annotation.get('completed_by')
        print(f"Warning: completed_by_info not found, user_id={user_id}")
        return jsonify({"status": "skipped", "reason": "no user info"})

    # Superuser는 skip
    if user_info.get('is_superuser', False):
        print(f"Skipping admin user: {user_info['email']}")
        return jsonify({
            "status": "skipped",
            "reason": "admin user",
            "user": user_info['email']
        })

    # 일반 사용자 annotation만 모델 성능 계산
    print(f"Processing annotation from user: {user_info['email']}")
    calculate_model_performance(payload, project_id)

    return jsonify({
        "status": "success",
        "user": user_info['email'],
        "action": action
    })


def calculate_model_performance(payload, project_id):
    """
    모델 성능을 계산합니다.
    """
    annotation = payload['annotation']
    task_id = annotation['task']

    # 모델 예측 결과와 사용자 annotation 비교
    # (실제 구현은 프로젝트에 따라 다름)
    print(f"Calculating performance for task {task_id} in project {project_id}")

    # ... 성능 계산 로직 ...

    # 백엔드에 결과 전송
    send_performance_to_backend(project_id, performance_score)


def send_performance_to_backend(project_id, score):
    """
    계산된 성능을 백엔드로 전송합니다.
    """
    print(f"Sending performance score {score} for project {project_id}")
    # ... 백엔드 API 호출 ...
```

### 2. 사용자 필터링

특정 사용자의 annotation만 처리하는 예시:

```python
def handle_webhook(project_id):
    payload = request.json
    user_info = payload.get('annotation', {}).get('completed_by_info', {})

    # 특정 이메일 도메인만 처리
    if not user_info.get('email', '').endswith('@company.com'):
        return jsonify({"status": "skipped", "reason": "external user"})

    # 특정 사용자만 처리
    allowed_users = ['reviewer1@company.com', 'reviewer2@company.com']
    if user_info.get('email') not in allowed_users:
        return jsonify({"status": "skipped", "reason": "not a reviewer"})

    # 처리 로직
    process_annotation(payload)
```

### 3. 사용자별 통계 수집

```python
from collections import defaultdict

# 사용자별 annotation 개수 추적
user_stats = defaultdict(int)

def handle_webhook(project_id):
    payload = request.json

    if payload.get('action') == 'ANNOTATION_CREATED':
        user_info = payload.get('annotation', {}).get('completed_by_info', {})
        user_email = user_info.get('email', 'unknown')

        user_stats[user_email] += 1

        print(f"User {user_email} has created {user_stats[user_email]} annotations")

    return jsonify({"status": "success"})
```

## Webhook 등록

### 1. API를 통한 등록

```python
import requests

LABEL_STUDIO_URL = "http://localhost:8080"
API_TOKEN = "your-api-token"

def register_webhook(project_id, webhook_url):
    """
    프로젝트에 webhook을 등록합니다.
    """
    url = f"{LABEL_STUDIO_URL}/api/webhooks"
    headers = {
        "Authorization": f"Token {API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "url": webhook_url,
        "organization": 1,
        "project": project_id,
        "active": True,
        "send_payload": True,  # ⚠️ 반드시 True로 설정
        "actions": [
            "ANNOTATION_CREATED",
            "ANNOTATION_UPDATED",
            "ANNOTATIONS_DELETED"
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    return response.json()

# 사용 예시
webhook_id = register_webhook(
    project_id=6,
    webhook_url="http://mlops.example.com/webhook/6"
)
print(f"Webhook registered with ID: {webhook_id}")
```

### 2. 주의사항

#### send_payload 옵션

**반드시 `send_payload: true`로 설정해야 합니다.**

- `send_payload: false` → action만 전송됨 (사용자 정보 없음)
  ```json
  {
    "action": "ANNOTATION_CREATED"
  }
  ```

- `send_payload: true` → 전체 payload 전송 (사용자 정보 포함)
  ```json
  {
    "action": "ANNOTATION_CREATED",
    "annotation": {
      "id": 17,
      "completed_by_info": { ... }
    }
  }
  ```

## 기술 구현

### 동작 원리

1. **Monkey Patching**: Label Studio의 `webhooks.utils.emit_webhooks` 함수를 래핑
2. **Payload 확장**: annotation 이벤트 감지 시 `enrich_annotation_payload()` 호출
3. **사용자 조회**: Django User 모델에서 `completed_by` ID로 사용자 정보 조회
4. **정보 추가**: `completed_by_info` 필드를 payload에 추가

### 코드 구조

```
custom-webhooks/
├── __init__.py          # 앱 초기화
├── apps.py              # Django 앱 설정
├── utils.py             # enrich_annotation_payload() 구현
├── signals.py           # Monkey patching 로직
└── tests.py             # 단위 테스트
```

### 주요 함수

#### `enrich_annotation_payload(payload)`

```python
def enrich_annotation_payload(payload):
    """
    Annotation webhook payload에 사용자 정보를 추가합니다.

    Args:
        payload (dict): 원본 webhook payload

    Returns:
        dict: 사용자 정보가 추가된 payload
    """
    if 'annotation' in payload and 'completed_by' in payload['annotation']:
        user_id = payload['annotation']['completed_by']
        user = User.objects.get(id=user_id)

        payload['annotation']['completed_by_info'] = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'is_superuser': user.is_superuser,
        }

    return payload
```

## 테스트

### 단위 테스트 실행

```bash
# Docker 컨테이너 내부에서
pytest custom_webhooks/tests.py -v
```

### 통합 테스트

1. **Webhook 등록**
   ```bash
   curl -X POST http://localhost:8080/api/webhooks \
     -H "Authorization: Token YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "http://webhook-receiver:8000/webhook/1",
       "project": 1,
       "send_payload": true,
       "actions": ["ANNOTATION_CREATED"]
     }'
   ```

2. **Annotation 생성**
   - Label Studio UI에서 annotation 생성
   - 또는 API로 생성

3. **Webhook 수신 확인**
   ```json
   {
     "action": "ANNOTATION_CREATED",
     "annotation": {
       "completed_by_info": {
         "email": "user@example.com",
         "is_superuser": false
       }
     }
   }
   ```

## 트러블슈팅

### 1. completed_by_info가 없는 경우

**증상**: Webhook payload에 `completed_by_info` 필드가 없음

**원인**:
- `send_payload: false`로 설정됨
- custom-webhooks 앱이 로드되지 않음
- Label Studio 버전 불일치

**해결**:
1. Webhook 설정 확인: `send_payload: true`인지 확인
2. 로그 확인: `Successfully patched webhooks.utils.emit_webhooks` 메시지 확인
3. 앱 설정 확인: `INSTALLED_APPS`에 `custom_webhooks` 포함 확인

### 2. User not found 에러

**증상**: 로그에 `User {user_id} not found` 경고 메시지

**원인**: 삭제된 사용자 또는 잘못된 user_id

**해결**: 이 경우 `completed_by_info`가 추가되지 않으며, `completed_by` ID만 사용 가능

## 성능 고려사항

### 데이터베이스 조회

- 각 webhook 전송 시 1회의 User 조회 발생
- User 모델은 일반적으로 인덱싱되어 있어 조회 속도가 빠름
- 예상 오버헤드: < 10ms

### 대안 (높은 트래픽 시)

성능이 중요한 경우:
1. **캐싱**: User 정보를 Redis에 캐싱
2. **배치 처리**: Webhook을 큐에 넣고 배치로 처리
3. **선택적 적용**: 특정 프로젝트만 활성화

## 보안 고려사항

### 민감 정보

`completed_by_info`에 포함되는 정보:
- ✅ `email`: 안전 (업무용 이메일)
- ✅ `username`: 안전
- ✅ `is_superuser`: 안전 (권한 플래그)

**포함되지 않는 정보**:
- ❌ 비밀번호
- ❌ 인증 토큰
- ❌ 개인 식별 정보 (전화번호 등)

### Webhook URL 보안

- HTTPS 사용 권장
- Webhook URL에 인증 토큰 포함 가능
- MLOps 시스템에서 요청 출처 검증 필요

## 참고 자료

- [Label Studio Webhook 공식 문서](https://labelstud.io/guide/webhooks)
- [Label Studio API Reference](https://api.labelstud.io/)
- [Django Signals Documentation](https://docs.djangoproject.com/en/stable/topics/signals/)
