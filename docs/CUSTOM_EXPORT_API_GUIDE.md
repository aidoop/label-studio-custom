# Custom Export API Guide

Label Studio Custom - SSO Edition의 Custom Export API 사용 가이드입니다.

## 개요

Custom Export API는 MLOps 시스템에서 모델 학습 및 성능 계산을 위해 필터링된 Task 데이터를 Export하는 기능을 제공합니다.

### 주요 기능

- ✅ **Superuser Annotation만 반환** (v1.20.0-sso.38)
  - `is_superuser=True`인 사용자의 annotation만 포함
  - Regular user annotations 자동 제외
  - Mixed annotations (superuser + regular user) → superuser만 포함
  - Draft annotations (`was_cancelled=True`) 자동 제외
- ✅ **응답 타입 선택** (`response_type`)
  - `count`: 건수만 반환 (페이징 계획용, 빠른 응답)
  - `data`: 전체 Task 데이터 반환 (기본값)
- ✅ **동적 날짜 필드 필터링** (`task.data` 내의 모든 날짜 필드 지원)
  - `search_date_field` 파라미터로 필드명 지정
  - 기본값: `source_created_at` (하위 호환성)
- ✅ 모델 버전 필터링 (`prediction.model_version`)
- ✅ 승인자 필터링 (`annotation.completed_by` - Superuser only)
- ✅ 선택적 페이징 지원 (기본: 전체 반환)
- ✅ N+1 쿼리 최적화 (Prefetch)
- ✅ SQL Injection 방지 (정규식 검증 + 파라미터화)

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
  "project_id": 1,                          // 필수: 프로젝트 ID
  "response_type": "data",                  // 옵션: 응답 타입 ("data" | "count", 기본값: "data")
  "search_from": "2025-01-01 00:00:00",    // 옵션: 검색 시작일
  "search_to": "2025-01-31 23:59:59",      // 옵션: 검색 종료일
  "search_date_field": "source_created_at", // 옵션: 날짜 필드명 (기본값: source_created_at)
  "model_version": "bert-v1",              // 옵션: 추론 모델 버전
  "confirm_user_id": 8,                     // 옵션: 승인자 User ID (Superuser만)
  "page": 1,                                // 옵션: 페이지 번호
  "page_size": 100                          // 옵션: 페이지 크기
}
```

### 파라미터 설명

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `project_id` | Integer | ✅ | Label Studio 프로젝트 ID |
| `response_type` | String | ❌ | 응답 타입 (기본값: `data`)<br>• `data`: 전체 Task 데이터 반환 (annotations, predictions 포함)<br>• `count`: 총 건수만 반환 (페이징 계획용, 성능 최적화) |
| `search_from` | DateTime | ❌ | 검색 시작일 (format: `yyyy-mm-dd hh:mi:ss` 또는 ISO 8601)<br>`task.data[search_date_field] >= search_from` |
| `search_to` | DateTime | ❌ | 검색 종료일 (format: `yyyy-mm-dd hh:mi:ss` 또는 ISO 8601)<br>`task.data[search_date_field] <= search_to` |
| `search_date_field` | String | ❌ | 검색할 날짜 필드명 (기본값: `source_created_at`)<br>`task.data` JSONB 내의 필드명<br>영문자, 숫자, 언더스코어만 허용 (최대 64자) |
| `model_version` | String | ❌ | 추론 모델 버전<br>prediction.model_version과 일치하는 Task만 반환 |
| `confirm_user_id` | Integer | ❌ | 승인자 User ID (Superuser만)<br>annotation.completed_by와 일치하고 is_superuser=true인 annotation만 반환 |
| `page` | Integer | ❌ | 페이지 번호 (1부터 시작)<br>page_size와 함께 제공되어야 함 |
| `page_size` | Integer | ❌ | 페이지당 Task 개수 (최대 10000)<br>page와 함께 제공되어야 함 |

### 필터링 조건 적용 순서

1. `project_id`로 기본 필터링
2. **Superuser annotation 필터링** (자동 적용, v1.20.0-sso.38)
   - `is_superuser=True`인 사용자의 annotation만 포함
   - `was_cancelled=False` (submit된 annotation만, draft 제외)
   - Regular user annotations 자동 제외
3. `search_from`, `search_to`로 날짜 범위 필터링
4. `model_version`으로 예측 모델 버전 필터링
5. `confirm_user_id`로 승인자 필터링 (특정 superuser)
6. 페이징 적용 (선택사항)

## Response

### 응답 형식

#### Count만 반환 (response_type='count')

페이징 계획 수립 시 사용합니다. Task 데이터를 직렬화하지 않아 빠른 응답이 가능합니다.

```json
{
  "total": 150
}
```

**사용 예시**: 전체 건수를 먼저 파악한 후, 적절한 `page_size`를 계산하여 데이터를 가져오는 워크플로우

#### 전체 데이터 반환 (response_type='data', 페이징 없음)

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
        "source_created_at": "2025-01-15 10:30:45"
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

### 예시 0: Count만 조회 (response_type='count')

페이징 계획 수립을 위해 전체 건수만 빠르게 조회합니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "response_type": "count"
  }'
```

**응답:**
```json
{
  "total": 1500
}
```

**사용 시나리오**: 전체 건수를 확인한 후 적절한 `page_size`를 계산하여 페이징 처리

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

### 예시 2: 날짜 범위 필터링 (기본 필드)

특정 기간의 Task만 가져옵니다. (`search_date_field` 생략 시 `source_created_at` 사용)

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

### 예시 2-1: 동적 날짜 필드 필터링 (센서 계측일시)

센서 계측일시(`mesure_at`) 기준으로 필터링합니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 23,
    "search_from": "2025-01-01 00:00:00",
    "search_to": "2025-12-31 23:59:59",
    "search_date_field": "mesure_at"
  }'
```

### 예시 2-2: 동적 날짜 필드 필터링 (원본 데이터 생성일)

원본 데이터 생성일(`original_created_at`) 기준으로 필터링합니다.

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "search_from": "2025-01-15 00:00:00",
    "search_to": "2025-01-20 23:59:59",
    "search_date_field": "original_created_at"
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

### 필터링 사용 (타임존 고려)

```python
from datetime import datetime, timezone
import pytz

# 방법 1: UTC 기준으로 필터링 (권장)
response = requests.post(
    f"{LABEL_STUDIO_URL}/api/custom/export/",
    headers=headers,
    json={
        "project_id": 1,
        "model_version": "bert-v1",
        "confirm_user_id": 8,  # 승인자만
        "search_from": "2025-01-01T00:00:00Z",  # UTC
        "search_to": "2025-01-31T23:59:59Z"     # UTC
    }
)

# 방법 2: 한국 시간(KST) 기준으로 필터링
kst = pytz.timezone('Asia/Seoul')
search_from = kst.localize(datetime(2025, 1, 1, 0, 0, 0))
search_to = kst.localize(datetime(2025, 1, 31, 23, 59, 59))

response = requests.post(
    f"{LABEL_STUDIO_URL}/api/custom/export/",
    headers=headers,
    json={
        "project_id": 1,
        "model_version": "bert-v1",
        "confirm_user_id": 8,
        "search_from": search_from.isoformat(),  # "2025-01-01T00:00:00+09:00"
        "search_to": search_to.isoformat()       # "2025-01-31T23:59:59+09:00"
    }
)

# 방법 3: 간단한 형식 (UTC로 간주됨)
response = requests.post(
    f"{LABEL_STUDIO_URL}/api/custom/export/",
    headers=headers,
    json={
        "project_id": 1,
        "model_version": "bert-v1",
        "confirm_user_id": 8,
        "search_from": "2025-01-01 00:00:00",  # UTC로 해석
        "search_to": "2025-01-31 23:59:59"     # UTC로 해석
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

1. **Annotation 필터링 규칙** (v1.20.0-sso.38 자동 적용)
   - **Superuser만 포함**: `is_superuser=True`인 사용자의 annotation만 반환
   - **Draft 제외**: `was_cancelled=True`인 임시 저장 annotation 자동 제외
   - **Regular user 제외**: 일반 사용자(is_superuser=False)의 annotation은 완전 제외
   - **Mixed annotations 처리**:
     - 하나의 Task에 superuser와 regular user가 모두 annotation한 경우
     - API는 해당 Task를 반환하되, **superuser annotations만 포함**
     - Regular user annotations는 응답에서 제외됨
   - **Multiple superuser annotations**:
     - 여러 superuser가 하나의 Task에 annotation한 경우
     - **모든 superuser annotations 포함**
     - `-created_at` 순서로 정렬 (최신순)
   - **Annotation 없는 Task**: 자동 제외 (superuser annotation이 없으면 반환 안 됨)

2. **source_created_at 필드**
   - Task 생성 시 `data.source_created_at` 필드를 포함해야 날짜 필터링이 작동합니다.
   - 누비슨 시스템에서 Task 생성 시 자동으로 포함됩니다.
   - **형식**: 일반 문자열 형식 사용 (예: `"2025-01-15 10:30:45"`)

3. **model_version 필드**
   - Prediction에 `model_version`을 포함해야 모델 버전 필터링이 작동합니다.
   - Task Import 시 prediction과 함께 전송하세요.

4. **승인자 필터**
   - `confirm_user_id`는 `is_superuser=true`인 사용자만 필터링합니다.
   - 일반 사용자의 annotation은 포함되지 않습니다.

5. **페이징**
   - `page`와 `page_size`는 함께 제공되어야 합니다.
   - 둘 다 없으면 전체 데이터를 반환합니다.

## 구현 세부사항

### Label Studio 오리지널 Serializer 사용

Custom Export API는 Label Studio 1.20.0의 표준 Serializer를 사용하여 데이터를 직렬화합니다:

- **PredictionSerializer** (`tasks.serializers.PredictionSerializer`)
  - 모든 prediction 필드 자동 포함 (`id`, `model_version`, `score`, `result`, `created_at`, `created_ago` 등)
  - Label Studio 표준 형식 준수

- **AnnotationSerializer** (`tasks.serializers.AnnotationSerializer`)
  - 모든 annotation 필드 자동 포함 (`id`, `completed_by`, `result`, `was_cancelled`, `created_at`, `updated_at`, `created_ago`, `created_username` 등)
  - Label Studio 표준 형식 준수

### MLOps 커스텀 기능

오리지널 Serializer를 사용하면서 MLOps에 필요한 기능 추가:

1. **completed_by_info Enrichment**
   - Annotation에 사용자 상세 정보 자동 추가
   - Webhook enrichment와 동일한 형식
   - 별도 API 호출 없이 사용자 정보 확인 가능

2. **필터링 기능**
   - **동적 날짜 필드 필터링** (`task.data` 내의 모든 날짜 필드 지원)
   - 모델 버전 필터링 (`prediction.model_version`)
   - 승인자 필터링 (Super User only)

3. **성능 최적화**
   - N+1 쿼리 방지 (Prefetch + Select Related)
   - 선택적 페이징 지원

### 오리지널 구현 준수의 장점

1. **호환성**: Label Studio 업데이트 시 새 필드 자동 포함
2. **표준 준수**: Label Studio API 응답 형식과 일치
3. **유지보수성**: 코드 중복 최소화, 간결한 구조
4. **확장성**: Label Studio의 기능 개선 자동 반영

## 보안

### SQL Injection 방지

Custom Export API는 다층 보안 메커니즘으로 SQL Injection을 방지합니다.

#### 1. 입력 검증 (Serializer 레벨)

`search_date_field` 파라미터는 정규식으로 검증됩니다:

```python
# 허용되는 패턴: 영문자, 숫자, 언더스코어만
^[a-zA-Z_][a-zA-Z0-9_]*$
```

**검증 규칙**:
- ✅ 첫 글자: 영문자 또는 언더스코어
- ✅ 이후 글자: 영문자, 숫자, 언더스코어
- ✅ 최대 길이: 64자
- ❌ 특수문자 금지: `'`, `"`, `;`, `--`, 공백 등

**정상 요청 예시**:
```json
{
  "search_date_field": "source_created_at"    // ✅ 통과
}
{
  "search_date_field": "mesure_at"            // ✅ 통과
}
{
  "search_date_field": "_timestamp"           // ✅ 통과
}
```

**악의적 요청 예시 (차단)**:
```json
{
  "search_date_field": "'; DROP TABLE--"      // ❌ 400 Bad Request
}
{
  "search_date_field": "source' OR '1'='1"    // ❌ 400 Bad Request
}
{
  "search_date_field": "data->>'password"     // ❌ 400 Bad Request
}
```

**에러 응답**:
```json
{
  "error": "Invalid request parameters",
  "details": {
    "search_date_field": [
      "필드명은 영문자, 숫자, 언더스코어(_)만 사용 가능합니다. 첫 글자는 영문자 또는 언더스코어여야 합니다."
    ]
  }
}
```

#### 2. 파라미터화된 쿼리 (ORM 레벨)

필드명도 파라미터로 전달하여 SQL Injection을 원천 차단합니다:

```python
# ❌ 이전 (취약)
queryset = queryset.extra(
    where=[f"(data->>'{search_date_field}') >= %s"],
    params=[search_from_str]
)

# ✅ 현재 (안전)
queryset = queryset.extra(
    where=["(data->>%s) >= %s"],
    params=[search_date_field, search_from_str]
)
```

#### 3. 다층 방어 (Defense in Depth)

```
Request
   ↓
[1] Serializer 정규식 검증
   ↓ (통과: source_created_at, mesure_at 등)
   ↓ (차단: "'; DROP TABLE--", "OR 1=1" 등)
   ↓
[2] Django ORM 파라미터화
   ↓ (자동 이스케이핑)
   ↓
PostgreSQL 쿼리 실행
```

## 버전 정보

- **최초 버전:** v1.20.0-sso.10
- **오리지널 Serializer 적용:** v1.20.0-sso.11
- **동적 날짜 필드 필터링 추가:** v1.20.0-sso.22
- **response_type 및 Mixed Annotation 처리:** v1.20.0-sso.38
- **Label Studio 기반 버전:** 1.20.0
- **문서 작성일:** 2025-10-28
- **최종 수정일:** 2025-11-20

## 관련 문서

- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [Webhook Guide](./WEBHOOK_GUIDE.md)
- [Admin User Management API](./ADMIN_USER_API_GUIDE.md)
