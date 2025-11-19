# Custom Export API 변경 사항 요약

**작성일**: 2025-11-19
**버전**: label-studio-custom:1.20.0-sso.37 (test)

---

## 변경 요청 사항

### 1. 검수자(Superuser) Annotation만 전송

- **문제**: 현재 API가 일반 사용자의 annotation도 포함하여 전송
- **요구사항**: 검수자(is_superuser=True)의 annotation만 포함
- **구현**: ✅ 완료

### 2. Annotation 없는 Task 제외

- **문제**: Annotation이 없는 task도 응답에 포함됨
- **요구사항**: Annotation이 있는 task만 반환
- **구현**: ✅ 완료

### 3. 임시 저장(Draft) Annotation 제외

- **문제**: Submit되지 않은 임시 저장 annotation 포함 여부 확인 필요
- **요구사항**: was_cancelled=False인 submit된 annotation만 포함
- **구현**: ✅ 완료

### 4. 건수 조회 기능 추가

- **배경**: 페이징 사용 전 총 건수 파악 필요 (timeout 방지)
- **요구사항**: response_type 파라미터로 건수만 조회 가능
- **구현**: ✅ 완료 (1안 선택: API 확장 방식)

---

## 변경된 파일

### 1. `/custom-api/export_serializers.py`

**추가된 필드**:

```python
# Lines 100-106
response_type = serializers.ChoiceField(
    choices=['data', 'count'],
    required=False,
    default='data',
    help_text="응답 타입 - 'data': Task 데이터 반환 (기본값), 'count': 건수만 반환"
)
```

### 2. `/custom-api/export.py`

**주요 변경 사항**:

#### a) 필수 필터 추가 (Lines 220-228)

```python
# 필수 필터: 검수자(Super User)의 유효한(submit된) annotation이 있는 task만
queryset = queryset.filter(
    annotations__completed_by__is_superuser=True,
    annotations__was_cancelled=False
).distinct()
```

#### b) Prefetch 최적화 (Lines 232-246)

```python
# 검수자의 유효한 annotation만 prefetch
valid_annotations_queryset = Annotation.objects.filter(
    completed_by__is_superuser=True,
    was_cancelled=False
).select_related('completed_by').order_by('-created_at')

queryset = queryset.prefetch_related(
    Prefetch('annotations', queryset=valid_annotations_queryset),
    Prefetch('predictions', queryset=Prediction.objects.order_by('-created_at'))
).select_related('project')
```

#### c) response_type='count' 처리 (Lines 128-132)

```python
# response_type='count'인 경우 건수만 반환 (성능 최적화)
if response_type == 'count':
    return Response(
        {"total": total},
        status=status.HTTP_200_OK
    )
```

#### d) Docstring 업데이트 (Lines 80-82)

```python
중요:
- 검수자(is_superuser=True)의 유효한(was_cancelled=False) annotation이 있는 task만 반환
- 임시 저장(draft) annotation은 제외됨
```

### 3. `/custom-api/tests.py`

**추가된 테스트 케이스** (6개):

1. `test_export_response_type_count` - 건수 조회 기능 테스트
2. `test_export_only_superuser_annotations` - Superuser annotation만 포함 확인
3. `test_export_exclude_cancelled_annotations` - Cancelled annotation 제외 확인
4. `test_export_exclude_tasks_without_annotations` - Annotation 없는 task 제외 확인
5. `test_export_exclude_tasks_with_only_regular_user_annotations` - 일반 사용자 annotation만 있는 task 제외 확인
6. `test_export_response_type_count_with_filters` - 필터와 함께 건수 조회 테스트

**수정된 기존 테스트**:

- 모든 기존 테스트에 annotation 추가 (필수 요구사항이 되었기 때문)

---

## API 사용법

### Request 예시

#### 1. 전체 Task 건수 조회

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "response_type": "count"
  }'
```

**Response**:

```json
{
  "total": 150
}
```

#### 2. 조건부 건수 조회 (날짜 + 모델 버전)

```bash
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "response_type": "count",
    "search_from": "2025-01-01 00:00:00",
    "search_to": "2025-01-31 23:59:59",
    "model_version": "bert-v1"
  }'
```

**Response**:

```json
{
  "total": 45
}
```

#### 3. 페이징을 사용한 데이터 조회

```bash
# Step 1: 건수 조회
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "response_type": "count"
  }'
# Response: {"total": 150}

# Step 2: 페이지 크기 계산 (예: 50개씩)
# total_pages = ceil(150 / 50) = 3

# Step 3: 첫 페이지 조회
curl -X POST http://localhost:8080/api/custom/export/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "response_type": "data",
    "page": 1,
    "page_size": 50
  }'
```

**Response**:

```json
{
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "has_next": true,
  "has_previous": false,
  "tasks": [...]
}
```

---

## 테스트 결과

### Unit Tests

```bash
cd /Users/super/Documents/GitHub/label-studio-custom
docker compose -f docker-compose.test.yml run --rm labelstudio python custom-api/tests.py

# 결과: 22+ tests passed ✅
```

### Integration Tests

```bash
cd /Users/super/Documents/GitHub/label-studio-custom
./test_custom_export_api.sh

# 결과: 9/9 tests passed ✅
```

**테스트 상세 결과**:

- ✅ Count-only response (3 tasks)
- ✅ Data response (3 tasks with IDs: 11, 10, 6)
- ✅ Superuser annotations only (is_superuser=true 확인)
- ✅ Model version filter (1 task with bert-v1)
- ✅ Date range filter (2 tasks in range)
- ✅ Pagination page 1 (2 tasks)
- ✅ Pagination page 2 (1 task)
- ✅ Confirm user ID filter (3 tasks)
- ✅ Request validation (error message in Korean)

**테스트 환경**: label-studio-sso-app (프로덕션 유사 환경)

---

## Breaking Changes ⚠️

### API 동작 변경

**이전 동작**:

- 모든 task를 반환 (annotation 여부와 무관)
- 일반 사용자의 annotation도 포함
- Draft annotation도 포함

**새로운 동작**:

- **검수자(is_superuser=True)의 유효한(was_cancelled=False) annotation이 있는 task만 반환**
- Annotation이 없는 task 제외
- 일반 사용자의 annotation만 있는 task 제외
- Draft/cancelled annotation 제외

### 영향 범위

**MLOps 시스템**:

1. 모델 학습 API 호출 코드
2. 모델 성능 계산 API 호출 코드

**마이그레이션 가이드**:

- 기존 코드 변경 불필요 (필터링이 자동 적용됨)
- 반환되는 task 수가 감소할 수 있음 (정상 동작)
- response_type='count'를 활용한 페이징 구현 권장

---

## 성능 최적화

### 1. N+1 Query 방지

- Prefetch 사용으로 annotation/prediction을 한 번에 로드
- select_related로 user 정보 join

### 2. response_type='count' 최적화

- 건수만 필요한 경우 task 직렬화 생략
- 페이징 전 건수 조회 시 성능 향상

### 3. Database-level Filtering

- 모든 필터링이 SQL 레벨에서 수행
- Python 코드에서의 후처리 없음

---

## 배포 체크리스트

### 개발 환경

- [x] 코드 변경 완료
- [x] Unit tests 통과
- [x] Integration tests 통과
- [x] Docker 이미지 빌드 성공

### 프로덕션 배포 전

- [ ] MLOps 팀에 변경 사항 공지
- [ ] Consumer 코드 검토 (필요시 수정)
- [ ] 개발 환경 배포 및 검증
- [ ] 운영 환경 배포

### 배포 후 모니터링

- [ ] API 응답 시간 모니터링
- [ ] 반환되는 task 수 변화 확인
- [ ] Database 쿼리 성능 확인
- [ ] 에러 로그 모니터링

---

## 관련 문서

- Integration Test Report: `/INTEGRATION_TEST_REPORT.md`
- Test Script: `/test_custom_export_api.sh`
- API Implementation: `/custom-api/export.py`
- Request/Response Serializers: `/custom-api/export_serializers.py`
- Unit Tests: `/custom-api/tests.py`

---
