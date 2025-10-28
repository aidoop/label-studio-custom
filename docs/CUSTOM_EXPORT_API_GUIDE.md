# Custom Export API Guide

Label Studio Custom - SSO Edition의 Custom Export API 사용 가이드입니다.

## 개요

Custom Export API는 MLOps 시스템에서 모델 학습 및 성능 계산을 위해 필터링된 Task 데이터를 Export하는 기능을 제공합니다.

### 주요 기능

- ✅ 날짜 범위 필터링 (`task.data.source_created_dt`)
- ✅ 모델 버전 필터링 (`prediction.model_version`)
- ✅ 승인자 필터링 (`annotation.completed_by` - Super User)
- ✅ 선택적 페이징 지원 (기본: 전체 반환)
- ✅ N+1 쿼리 최적화 (Prefetch)

## API Endpoint

```
POST /api/custom/export/
```

### 인증

모든 인증된 사용자가 접근 가능합니다.

**Authorization Header:**
```
Authorization: Token <your-api-token>
```

또는 JWT 토큰:
```
Authorization: Bearer <jwt-token>
```

## Request

### Request Body

```json
{
  "project_id": 1,                        // 필수: 프로젝트 ID
  "search_from": "2025-01-01 00:00:00",  // 옵션: 검색 시작일
  "search_to": "2025-01-31 23:59:59",    // 옵션: 검색 종료일
  "model_version": "bert-v1",            // 옵션: 추론 모델 버전
  "confirm_user_id": 8,                   // 옵션: 승인자 User ID
  "page": 1,                              // 옵션: 페이지 번호
  "page_size": 100                        // 옵션: 페이지 크기
}
```

### 파라미터 설명

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `project_id` | Integer | ✅ | Label Studio 프로젝트 ID |
| `search_from` | String | ❌ | 검색 시작일 (format: `yyyy-mm-dd hh:mi:ss`)<br>task.data.source_created_dt >= search_from |
| `search_to` | String | ❌ | 검색 종료일 (format: `yyyy-mm-dd hh:mi:ss`)<br>task.data.source_created_dt <= search_to |
| `model_version` | String | ❌ | 추론 모델 버전<br>prediction.model_version과 일치하는 Task만 반환 |
| `confirm_user_id` | Integer | ❌ | 승인자 User ID<br>annotation.completed_by와 일치하고 is_superuser=true인 annotation만 반환 |
| `page` | Integer | ❌ | 페이지 번호 (1부터 시작)<br>page_size와 함께 제공되어야 함 |
| `page_size` | Integer | ❌ | 페이지당 Task 개수 (최대 10000)<br>page와 함께 제공되어야 함 |

### 필터링 조건 적용 순서

1. `project_id`로 기본 필터링
2. `search_from`, `search_to`로 날짜 범위 필터링
3. `model_version`으로 예측 모델 버전 필터링
4. `confirm_user_id`로 승인자 필터링
5. 페이징 적용 (선택사항)

## Response

### 응답 형식

#### 전체 반환 (페이징 없음)

```json
{
  "total": 150,
  "tasks": [
    {
      "id": 123,
      "project_id": 1,
      "data": {
        "text": "샘플 텍스트",
        "image": "https://example.com/image.jpg",
        "source_created_dt": "2025-01-15 10:30:45"
      },
      "meta": {},
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T11:00:00Z",
      "is_labeled": true,
      "predictions": [
        {
          "id": 789,
          "model_version": "bert-v1",
          "score": 0.95,
          "result": [
            {
              "from_name": "sentiment",
              "to_name": "text",
              "type": "choices",
              "value": {
                "choices": ["Positive"]
              }
            }
          ],
          "created_at": "2025-01-15T10:35:00Z"
        }
      ],
      "annotations": [
        {
          "id": 456,
          "completed_by": 8,
          "completed_by_info": {
            "id": 8,
            "email": "admin@example.com",
            "username": "admin",
            "is_superuser": true
          },
          "result": [
            {
              "from_name": "sentiment",
              "to_name": "text",
              "type": "choices",
              "value": {
                "choices": ["Positive"]
              }
            }
          ],
          "was_cancelled": false,
          "created_at": "2025-01-15T11:00:00Z",
          "updated_at": "2025-01-15T11:05:00Z"
        }
      ]
    }
  ]
}
```

#### 페이징 적용

```json
{
  "total": 1500,
  "page": 1,
  "page_size": 100,
  "total_pages": 15,
  "has_next": true,
  "has_previous": false,
  "tasks": [ /* 100개 Task */ ]
}
```

### 응답 필드 설명

| 필드 | 타입 | 설명 |
|-----|------|------|
| `total` | Integer | 필터링된 전체 Task 개수 |
| `page` | Integer | 현재 페이지 번호 (페이징 시) |
| `page_size` | Integer | 페이지당 Task 개수 (페이징 시) |
| `total_pages` | Integer | 전체 페이지 수 (페이징 시) |
| `has_next` | Boolean | 다음 페이지 존재 여부 (페이징 시) |
| `has_previous` | Boolean | 이전 페이지 존재 여부 (페이징 시) |
| `tasks` | Array | Task 목록 |

### Task 객체 구조

| 필드 | 타입 | 설명 |
|-----|------|------|
| `id` | Integer | Task ID |
| `project_id` | Integer | 프로젝트 ID |
| `data` | Object | 입력 데이터 (JSON) |
| `meta` | Object | 메타데이터 (JSON) |
| `created_at` | DateTime | Task 생성 시간 |
| `updated_at` | DateTime | Task 수정 시간 |
| `is_labeled` | Boolean | 라벨링 완료 여부 |
| `predictions` | Array | 예측 목록 |
| `annotations` | Array | Annotation 목록 |

## 사용 예시

### 예시 1: 전체 Task Export (페이징 없음)

모델 학습을 위해 프로젝트의 모든 Task를 가져옵니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1
  }'
```

### 예시 2: 날짜 범위 필터링

특정 기간의 Task만 가져옵니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "search_from": "2025-01-01 00:00:00",
    "search_to": "2025-01-31 23:59:59"
  }'
```

### 예시 3: 모델 버전 필터링

특정 모델 버전으로 예측된 Task만 가져옵니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "model_version": "bert-v1"
  }'
```

### 예시 4: 승인자 필터링

특정 승인자(Super User)가 라벨링한 Task만 가져옵니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "confirm_user_id": 8
  }'
```

### 예시 5: 페이징 사용

대용량 데이터를 페이징으로 나눠서 가져옵니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "page": 1,
    "page_size": 100
  }'
```

### 예시 6: 모든 필터 조합

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "search_from": "2025-01-01 00:00:00",
    "search_to": "2025-01-31 23:59:59",
    "model_version": "bert-v1",
    "confirm_user_id": 8,
    "page": 1,
    "page_size": 100
  }'
```

## Python 클라이언트 예시

### 기본 사용법

```python
import requests

LABEL_STUDIO_URL = "http://localhost:8080"
API_TOKEN = "YOUR_API_TOKEN"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# 전체 Export
response = requests.post(
    f"{LABEL_STUDIO_URL}/api/custom/export/",
    headers=headers,
    json={
        "project_id": 1
    }
)

data = response.json()
print(f"Total tasks: {data['total']}")
print(f"Tasks: {len(data['tasks'])}")
```

### 페이징 사용

```python
def fetch_all_tasks(project_id, page_size=100):
    """페이징을 사용하여 모든 Task 가져오기"""
    all_tasks = []
    page = 1

    while True:
        response = requests.post(
            f"{LABEL_STUDIO_URL}/api/custom/export/",
            headers=headers,
            json={
                "project_id": project_id,
                "page": page,
                "page_size": page_size
            }
        )

        data = response.json()
        all_tasks.extend(data['tasks'])

        print(f"Fetched page {page}/{data['total_pages']}")

        if not data.get('has_next'):
            break

        page += 1

    return all_tasks

# 사용
tasks = fetch_all_tasks(project_id=1)
print(f"Total fetched: {len(tasks)} tasks")
```

### 필터링 사용

```python
# 모델 성능 계산용 Export
response = requests.post(
    f"{LABEL_STUDIO_URL}/api/custom/export/",
    headers=headers,
    json={
        "project_id": 1,
        "model_version": "bert-v1",
        "confirm_user_id": 8,  # 승인자만
        "search_from": "2025-01-01 00:00:00",
        "search_to": "2025-01-31 23:59:59"
    }
)

data = response.json()

# 모델 성능 계산
correct = 0
total = 0

for task in data['tasks']:
    if not task['predictions'] or not task['annotations']:
        continue

    prediction = task['predictions'][0]['result']
    annotation = task['annotations'][0]['result']

    # 예측과 annotation 비교
    if prediction == annotation:
        correct += 1
    total += 1

accuracy = correct / total if total > 0 else 0
print(f"Model Accuracy: {accuracy:.2%} ({correct}/{total})")
```

## 에러 처리

### 400 Bad Request

```json
{
  "error": "Invalid request parameters",
  "details": {
    "project_id": ["This field is required."]
  }
}
```

**원인:**
- 필수 파라미터 누락
- 잘못된 데이터 타입
- page와 page_size 중 하나만 제공

### 404 Not Found

```json
{
  "error": "Project with id 999 does not exist"
}
```

**원인:**
- 존재하지 않는 project_id

### 401 Unauthorized

**원인:**
- 인증 토큰 누락 또는 만료

## 성능 최적화

### 1. 페이징 사용

대용량 데이터(10,000개 이상)는 페이징을 사용하세요:

```json
{
  "project_id": 1,
  "page": 1,
  "page_size": 1000
}
```

### 2. 필터링 활용

필요한 데이터만 가져오세요:

```json
{
  "project_id": 1,
  "model_version": "bert-v1",
  "search_from": "2025-01-01 00:00:00"
}
```

### 3. N+1 쿼리 최적화

API는 자동으로 `prefetch_related`를 사용하여 최적화되어 있습니다.

## MLOps 통합 시나리오

### 시나리오 1: 모델 학습

```python
# 1. 전체 Task Export
response = requests.post(url, json={"project_id": 1})
tasks = response.json()['tasks']

# 2. Training 데이터 준비
training_data = []
for task in tasks:
    if task['annotations']:
        annotation = task['annotations'][0]
        training_data.append({
            'text': task['data']['text'],
            'label': annotation['result'][0]['value']['choices'][0]
        })

# 3. 모델 학습
train_model(training_data)
```

### 시나리오 2: 모델 성능 계산

```python
# 1. 특정 모델 버전의 Task Export
response = requests.post(url, json={
    "project_id": 1,
    "model_version": "bert-v1",
    "confirm_user_id": 8  # 승인자만
})

tasks = response.json()['tasks']

# 2. 성능 계산
correct = sum(
    1 for task in tasks
    if task['predictions'] and task['annotations']
    and task['predictions'][0]['result'] == task['annotations'][0]['result']
)

accuracy = correct / len(tasks)
print(f"Model Performance: {accuracy:.2%}")

# 3. 누비슨 백엔드로 결과 전송
send_performance_to_backend(model_version="bert-v1", accuracy=accuracy)
```

## 주의사항

1. **source_created_dt 필드**
   - Task 생성 시 `data.source_created_dt` 필드를 포함해야 날짜 필터링이 작동합니다.
   - 누비슨 시스템에서 Task 생성 시 자동으로 포함됩니다.

2. **model_version 필드**
   - Prediction에 `model_version`을 포함해야 모델 버전 필터링이 작동합니다.
   - Task Import 시 prediction과 함께 전송하세요.

3. **승인자 필터**
   - `confirm_user_id`는 `is_superuser=true`인 사용자만 필터링합니다.
   - 일반 사용자의 annotation은 포함되지 않습니다.

4. **페이징**
   - `page`와 `page_size`는 함께 제공되어야 합니다.
   - 둘 다 없으면 전체 데이터를 반환합니다.

## 버전 정보

- **최초 버전:** v1.20.0-sso.10
- **Label Studio 기반 버전:** 1.20.0
- **문서 작성일:** 2025-10-28

## 관련 문서

- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [Webhook Guide](./WEBHOOK_GUIDE.md)
- [Admin User Management API](./ADMIN_USER_API_GUIDE.md)
