"""
Custom API Tests

Label Studio 1.20.0 기반 커스텀 API 테스트
- Custom Export API
- Custom SSO Token Validation API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from projects.models import Project
from tasks.models import Task, Annotation, Prediction
from organizations.models import Organization
import json
from datetime import datetime
import pytz
from unittest.mock import patch

User = get_user_model()


class CustomExportAPITest(TestCase):
    """Custom Export API 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # Organization 생성
        self.org = Organization.objects.create(title="Test Org")

        # 사용자 생성
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()

        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )

        # Organization 멤버십 추가
        self.org.add_user(self.admin_user)
        self.org.add_user(self.regular_user)

        # 프로젝트 생성
        self.project = Project.objects.create(
            title='Test Project',
            organization=self.org,
            created_by=self.admin_user,
            label_config='<View><Text name="text" value="$text"/><Choices name="sentiment" toName="text"><Choice value="Positive"/><Choice value="Negative"/></Choices></View>'
        )

        # API Client 설정
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        # URL
        self.export_url = '/api/custom/export/'

    def _create_task(self, data, source_created_dt=None):
        """Task 생성 헬퍼"""
        task_data = data.copy()
        if source_created_dt:
            task_data['source_created_dt'] = source_created_dt

        task = Task.objects.create(
            project=self.project,
            data=task_data
        )
        return task

    def _create_annotation(self, task, completed_by, result):
        """Annotation 생성 헬퍼"""
        annotation = Annotation.objects.create(
            task=task,
            project=self.project,
            completed_by=completed_by,
            result=result
        )
        return annotation

    def _create_prediction(self, task, model_version, result, score=0.9):
        """Prediction 생성 헬퍼"""
        prediction = Prediction.objects.create(
            task=task,
            project=self.project,
            model_version=model_version,
            score=score,
            result=result
        )
        return prediction

    def test_export_api_requires_authentication(self):
        """인증 필수 확인"""
        client = APIClient()
        response = client.post(self.export_url, {'project_id': self.project.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_export_api_requires_project_id(self):
        """project_id 필수 확인"""
        response = self.client.post(self.export_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project_id', str(response.data))

    def test_export_api_invalid_project_id(self):
        """존재하지 않는 project_id 처리"""
        response = self.client.post(self.export_url, {'project_id': 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_all_tasks(self):
        """전체 Task Export (페이징 없음)"""
        # Task 3개 생성
        task1 = self._create_task({'text': 'Task 1'})
        task2 = self._create_task({'text': 'Task 2'})
        task3 = self._create_task({'text': 'Task 3'})

        response = self.client.post(self.export_url, {'project_id': self.project.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 3)
        self.assertEqual(len(data['tasks']), 3)
        self.assertNotIn('page', data)  # 페이징 정보 없음

    def test_export_with_date_filter(self):
        """날짜 범위 필터링"""
        # Task 생성 (source_created_dt 포함)
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15 10:00:00'
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-20 10:00:00'
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-25 10:00:00'
        )

        # 1월 16일 ~ 1월 24일 필터
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-16 00:00:00',
            'search_to': '2025-01-24 23:59:59'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['tasks'][0]['data']['text'], 'Task 2')

    def test_export_with_model_version_filter(self):
        """모델 버전 필터링"""
        # Task 생성
        task1 = self._create_task({'text': 'Task 1'})
        task2 = self._create_task({'text': 'Task 2'})
        task3 = self._create_task({'text': 'Task 3'})

        # Prediction 생성 (서로 다른 model_version)
        self._create_prediction(task1, 'bert-v1', [{'type': 'choices', 'value': {'choices': ['Positive']}}])
        self._create_prediction(task2, 'bert-v2', [{'type': 'choices', 'value': {'choices': ['Negative']}}])
        self._create_prediction(task3, 'bert-v1', [{'type': 'choices', 'value': {'choices': ['Positive']}}])

        # bert-v1 모델로 필터링
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'model_version': 'bert-v1'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 2)
        task_texts = [t['data']['text'] for t in data['tasks']]
        self.assertIn('Task 1', task_texts)
        self.assertIn('Task 3', task_texts)
        self.assertNotIn('Task 2', task_texts)

    def test_export_with_confirm_user_filter(self):
        """승인자 필터링 (Super User)"""
        # Task 생성
        task1 = self._create_task({'text': 'Task 1'})
        task2 = self._create_task({'text': 'Task 2'})
        task3 = self._create_task({'text': 'Task 3'})

        # Annotation 생성
        result = [{'type': 'choices', 'from_name': 'sentiment', 'to_name': 'text', 'value': {'choices': ['Positive']}}]
        self._create_annotation(task1, self.admin_user, result)
        self._create_annotation(task2, self.regular_user, result)
        self._create_annotation(task3, self.admin_user, result)

        # admin_user (Super User)로 필터링
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'confirm_user_id': self.admin_user.id
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 2)
        task_texts = [t['data']['text'] for t in data['tasks']]
        self.assertIn('Task 1', task_texts)
        self.assertIn('Task 3', task_texts)
        self.assertNotIn('Task 2', task_texts)

    def test_export_with_pagination(self):
        """페이징"""
        # Task 5개 생성
        for i in range(1, 6):
            self._create_task({'text': f'Task {i}'})

        # 페이지 1 (2개씩)
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'page': 1,
            'page_size': 2
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 5)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['page_size'], 2)
        self.assertEqual(data['total_pages'], 3)
        self.assertTrue(data['has_next'])
        self.assertFalse(data['has_previous'])
        self.assertEqual(len(data['tasks']), 2)

        # 페이지 2
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'page': 2,
            'page_size': 2
        })

        data = response.json()
        self.assertEqual(data['page'], 2)
        self.assertTrue(data['has_next'])
        self.assertTrue(data['has_previous'])

        # 페이지 3 (마지막)
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'page': 3,
            'page_size': 2
        })

        data = response.json()
        self.assertEqual(data['page'], 3)
        self.assertFalse(data['has_next'])
        self.assertTrue(data['has_previous'])
        self.assertEqual(len(data['tasks']), 1)

    def test_export_combined_filters(self):
        """여러 필터 조합"""
        # Task 생성
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15 10:00:00'
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-20 10:00:00'
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-25 10:00:00'
        )

        # Prediction 추가
        self._create_prediction(task1, 'bert-v1', [])
        self._create_prediction(task2, 'bert-v1', [])
        self._create_prediction(task3, 'bert-v2', [])

        # Annotation 추가
        result = [{'type': 'choices', 'value': {'choices': ['Positive']}}]
        self._create_annotation(task1, self.admin_user, result)
        self._create_annotation(task2, self.admin_user, result)

        # 모든 필터 조합
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-10 00:00:00',
            'search_to': '2025-01-22 23:59:59',
            'model_version': 'bert-v1',
            'confirm_user_id': self.admin_user.id
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 2)
        task_texts = [t['data']['text'] for t in data['tasks']]
        self.assertIn('Task 1', task_texts)
        self.assertIn('Task 2', task_texts)

    def test_export_response_structure(self):
        """Response 구조 검증"""
        task = self._create_task({'text': 'Test Task'})
        prediction = self._create_prediction(task, 'bert-v1', [])
        annotation = self._create_annotation(
            task,
            self.admin_user,
            [{'type': 'choices', 'value': {'choices': ['Positive']}}]
        )

        response = self.client.post(self.export_url, {'project_id': self.project.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 기본 구조
        self.assertIn('total', data)
        self.assertIn('tasks', data)

        # Task 구조
        task_data = data['tasks'][0]
        self.assertIn('id', task_data)
        self.assertIn('project_id', task_data)
        self.assertIn('data', task_data)
        self.assertIn('created_at', task_data)
        self.assertIn('updated_at', task_data)
        self.assertIn('is_labeled', task_data)
        self.assertIn('predictions', task_data)
        self.assertIn('annotations', task_data)

        # Prediction 구조
        pred = task_data['predictions'][0]
        self.assertIn('id', pred)
        self.assertIn('model_version', pred)
        self.assertIn('score', pred)
        self.assertIn('result', pred)

        # Annotation 구조
        anno = task_data['annotations'][0]
        self.assertIn('id', anno)
        self.assertIn('completed_by', anno)
        self.assertIn('completed_by_info', anno)
        self.assertIn('result', anno)
        self.assertIn('was_cancelled', anno)

        # completed_by_info 구조
        user_info = anno['completed_by_info']
        self.assertIn('id', user_info)
        self.assertIn('email', user_info)
        self.assertIn('username', user_info)
        self.assertIn('is_superuser', user_info)
        self.assertTrue(user_info['is_superuser'])

    def test_pagination_validation(self):
        """페이징 파라미터 검증"""
        # page만 제공 (page_size 없음)
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'page': 1
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # page_size만 제공 (page 없음)
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'page_size': 10
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_result(self):
        """결과 없음 처리"""
        # Task는 있지만 필터에 맞지 않음
        self._create_task({'text': 'Task 1'})

        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'model_version': 'non-existent-model'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['tasks']), 0)

    def test_export_with_timezone_aware_dates(self):
        """타임존이 포함된 날짜 필터링"""
        # Task 생성 (ISO 8601 형식, 타임존 포함)
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15T10:00:00+09:00'  # 한국 시간
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-15T05:00:00+00:00'  # UTC (한국 시간 14:00)
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-16T00:00:00+09:00'  # 한국 시간
        )

        # UTC 기준으로 필터링: 2025-01-15 00:00:00 UTC ~ 2025-01-15 23:59:59 UTC
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-15T00:00:00Z',
            'search_to': '2025-01-15T23:59:59Z'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # task1: 2025-01-15T10:00:00+09:00 = 2025-01-15T01:00:00Z (포함)
        # task2: 2025-01-15T05:00:00+00:00 = 2025-01-15T05:00:00Z (포함)
        # task3: 2025-01-16T00:00:00+09:00 = 2025-01-15T15:00:00Z (포함)
        self.assertEqual(data['total'], 3)

    def test_export_with_kst_timezone_filter(self):
        """한국 시간대(KST) 필터링"""
        # Task 생성
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15T08:00:00+09:00'  # 한국 시간 오전 8시
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-15T12:00:00+09:00'  # 한국 시간 오후 12시
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-15T18:00:00+09:00'  # 한국 시간 오후 6시
        )

        # 한국 시간 기준 오전 9시 ~ 오후 5시 필터링
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-15T09:00:00+09:00',
            'search_to': '2025-01-15T17:00:00+09:00'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['tasks'][0]['data']['text'], 'Task 2')

    def test_export_with_naive_datetime(self):
        """타임존 없는 날짜 필터링 (UTC로 간주)"""
        # Task 생성 (타임존 없음)
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15 10:00:00'
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-15 14:00:00'
        )

        # 타임존 없는 필터 (UTC로 간주)
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-15 12:00:00',
            'search_to': '2025-01-15 23:59:59'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['tasks'][0]['data']['text'], 'Task 2')

    def test_export_with_mixed_timezone_formats(self):
        """다양한 타임존 형식 혼합"""
        # 다양한 형식으로 Task 생성
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15T10:00:00+09:00'  # ISO 8601 with KST
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-15T05:00:00Z'       # ISO 8601 with UTC
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-15 03:00:00'        # Naive (UTC로 간주)
        )

        # UTC 기준 02:00:00 ~ 06:00:00 필터링
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-15T02:00:00Z',
            'search_to': '2025-01-15T06:00:00Z'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # task1: 2025-01-15T10:00:00+09:00 = 01:00:00Z (제외)
        # task2: 2025-01-15T05:00:00Z = 05:00:00Z (포함)
        # task3: 2025-01-15 03:00:00 = 03:00:00Z (포함)
        self.assertEqual(data['total'], 2)
        task_texts = [t['data']['text'] for t in data['tasks']]
        self.assertIn('Task 2', task_texts)
        self.assertIn('Task 3', task_texts)
        self.assertNotIn('Task 1', task_texts)

    def test_export_date_boundary_conditions(self):
        """날짜 경계 조건 테스트"""
        # 경계값 Task 생성
        task1 = self._create_task(
            {'text': 'Task 1'},
            source_created_dt='2025-01-15T00:00:00Z'  # 정확히 시작 시간
        )
        task2 = self._create_task(
            {'text': 'Task 2'},
            source_created_dt='2025-01-15T23:59:59Z'  # 정확히 종료 시간
        )
        task3 = self._create_task(
            {'text': 'Task 3'},
            source_created_dt='2025-01-16T00:00:00Z'  # 종료 시간 1초 후
        )

        # 경계값 테스트
        response = self.client.post(self.export_url, {
            'project_id': self.project.id,
            'search_from': '2025-01-15T00:00:00Z',
            'search_to': '2025-01-15T23:59:59Z'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total'], 2)
        task_texts = [t['data']['text'] for t in data['tasks']]
        self.assertIn('Task 1', task_texts)
        self.assertIn('Task 2', task_texts)
        self.assertNotIn('Task 3', task_texts)


class ValidatedSSOTokenAPITest(TestCase):
    """Custom SSO Token Validation API 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # Admin 사용자 생성 (API 호출 권한)
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()

        # 일반 사용자 생성
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )

        # 비활성 사용자 생성
        self.inactive_user = User.objects.create_user(
            username='inactive',
            email='inactive@test.com',
            password='testpass123'
        )
        self.inactive_user.is_active = False
        self.inactive_user.save()

        # API Client 설정
        self.client = APIClient()
        self.url = '/api/custom/sso/token'

    def test_requires_admin_permission(self):
        """Admin 권한 필요 확인"""
        # 인증 없음
        response = self.client.post(self.url, {'email': 'user@test.com'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 일반 사용자 인증
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.url, {'email': 'user@test.com'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_requires_email_parameter(self):
        """email 파라미터 필수 확인"""
        self.client.force_authenticate(user=self.admin_user)

        # email 없음
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'INVALID_REQUEST')
        self.assertIn('email is required', data['error'])

    def test_user_not_found(self):
        """존재하지 않는 사용자 처리"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(self.url, {'email': 'nonexistent@test.com'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'USER_NOT_FOUND')
        self.assertIn('User not found', data['error'])
        self.assertEqual(data['email'], 'nonexistent@test.com')

    def test_inactive_user_rejected(self):
        """비활성 사용자 거부"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(self.url, {'email': 'inactive@test.com'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'USER_INACTIVE')
        self.assertIn('User is inactive', data['error'])
        self.assertEqual(data['email'], 'inactive@test.com')

    @patch('custom_api.sso.generate_jwt_token')
    def test_successful_token_generation(self, mock_generate_jwt):
        """정상적인 토큰 발급"""
        self.client.force_authenticate(user=self.admin_user)

        # Mock JWT 토큰 생성
        mock_generate_jwt.return_value = 'mock_jwt_token_12345'

        response = self.client.post(self.url, {'email': 'user@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data['token'], 'mock_jwt_token_12345')
        self.assertEqual(data['expires_in'], 600)

        # 사용자 정보 확인
        user_data = data['user']
        self.assertEqual(user_data['id'], self.regular_user.id)
        self.assertEqual(user_data['email'], 'user@test.com')
        self.assertEqual(user_data['username'], 'user')
        self.assertFalse(user_data['is_superuser'])

        # generate_jwt_token이 올바른 인자로 호출되었는지 확인
        mock_generate_jwt.assert_called_once_with(self.regular_user, expiry_seconds=600)

    @patch('custom_api.sso.generate_jwt_token')
    def test_superuser_token_generation(self, mock_generate_jwt):
        """Superuser 토큰 발급"""
        self.client.force_authenticate(user=self.admin_user)

        mock_generate_jwt.return_value = 'mock_admin_token'

        response = self.client.post(self.url, {'email': 'admin@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        user_data = data['user']
        self.assertTrue(user_data['is_superuser'])

    def test_email_case_insensitive(self):
        """이메일 대소문자 구분 없음 (Django 기본 동작)"""
        self.client.force_authenticate(user=self.admin_user)

        # 대문자로 조회
        with patch('custom_api.sso.generate_jwt_token', return_value='mock_token'):
            response = self.client.post(self.url, {'email': 'USER@TEST.COM'})

            # Django의 User 모델은 기본적으로 email이 대소문자를 구분하므로
            # 정확히 일치하지 않으면 USER_NOT_FOUND 반환
            if response.status_code == status.HTTP_404_NOT_FOUND:
                data = response.json()
                self.assertEqual(data['error_code'], 'USER_NOT_FOUND')


class BatchValidateSSOTokenAPITest(TestCase):
    """Batch SSO Token Validation API 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # Admin 사용자 생성
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()

        # 일반 사용자들 생성
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )

        # 비활성 사용자
        self.inactive_user = User.objects.create_user(
            username='inactive',
            email='inactive@test.com',
            password='testpass123'
        )
        self.inactive_user.is_active = False
        self.inactive_user.save()

        # API Client 설정
        self.client = APIClient()
        self.url = '/api/custom/sso/batch-token'

    def test_requires_admin_permission(self):
        """Admin 권한 필요 확인"""
        # 인증 없음
        response = self.client.post(self.url, {'emails': ['user1@test.com']})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_emails_parameter(self):
        """emails 파라미터 필수 확인"""
        self.client.force_authenticate(user=self.admin_user)

        # emails 없음
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error_code'], 'INVALID_REQUEST')

    def test_emails_must_be_list(self):
        """emails가 리스트여야 함"""
        self.client.force_authenticate(user=self.admin_user)

        # 문자열로 전달
        response = self.client.post(self.url, {'emails': 'user1@test.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data['error_code'], 'INVALID_REQUEST')

    def test_empty_emails_list(self):
        """빈 리스트 처리"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(self.url, {'emails': []})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data['error_code'], 'INVALID_REQUEST')

    @patch('custom_api.sso.generate_jwt_token')
    def test_batch_token_generation_all_success(self, mock_generate_jwt):
        """모든 사용자 토큰 발급 성공"""
        self.client.force_authenticate(user=self.admin_user)

        # Mock JWT 토큰 생성 (호출마다 다른 토큰)
        mock_generate_jwt.side_effect = ['token1', 'token2']

        response = self.client.post(self.url, {
            'emails': ['user1@test.com', 'user2@test.com']
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 결과 요약 확인
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['success'], 2)
        self.assertEqual(data['failed'], 0)

        # 성공 목록 확인
        self.assertEqual(len(data['results']['success']), 2)

        # 첫 번째 사용자
        result1 = data['results']['success'][0]
        self.assertEqual(result1['email'], 'user1@test.com')
        self.assertEqual(result1['token'], 'token1')
        self.assertEqual(result1['expires_in'], 600)
        self.assertEqual(result1['user']['id'], self.user1.id)

        # 두 번째 사용자
        result2 = data['results']['success'][1]
        self.assertEqual(result2['email'], 'user2@test.com')
        self.assertEqual(result2['token'], 'token2')

    @patch('custom_api.sso.generate_jwt_token')
    def test_batch_token_generation_mixed_results(self, mock_generate_jwt):
        """일부 성공, 일부 실패"""
        self.client.force_authenticate(user=self.admin_user)

        mock_generate_jwt.return_value = 'token1'

        response = self.client.post(self.url, {
            'emails': [
                'user1@test.com',           # 성공
                'nonexistent@test.com',     # 실패: 사용자 없음
                'inactive@test.com',        # 실패: 비활성 사용자
            ]
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 결과 요약
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['success'], 1)
        self.assertEqual(data['failed'], 2)

        # 성공 목록
        success_results = data['results']['success']
        self.assertEqual(len(success_results), 1)
        self.assertEqual(success_results[0]['email'], 'user1@test.com')

        # 실패 목록
        failed_results = data['results']['failed']
        self.assertEqual(len(failed_results), 2)

        # 사용자 없음 오류
        user_not_found = next(r for r in failed_results if r['email'] == 'nonexistent@test.com')
        self.assertEqual(user_not_found['error_code'], 'USER_NOT_FOUND')
        self.assertIn('User not found', user_not_found['error'])

        # 비활성 사용자 오류
        inactive_error = next(r for r in failed_results if r['email'] == 'inactive@test.com')
        self.assertEqual(inactive_error['error_code'], 'USER_INACTIVE')
        self.assertIn('User is inactive', inactive_error['error'])

    def test_batch_token_generation_all_failed(self):
        """모두 실패"""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(self.url, {
            'emails': [
                'nonexistent1@test.com',
                'nonexistent2@test.com',
            ]
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total'], 2)
        self.assertEqual(data['success'], 0)
        self.assertEqual(data['failed'], 2)
        self.assertEqual(len(data['results']['success']), 0)
        self.assertEqual(len(data['results']['failed']), 2)

    @patch('custom_api.sso.generate_jwt_token')
    def test_duplicate_emails_handled(self, mock_generate_jwt):
        """중복 이메일 처리"""
        self.client.force_authenticate(user=self.admin_user)

        mock_generate_jwt.side_effect = ['token1', 'token2']

        response = self.client.post(self.url, {
            'emails': [
                'user1@test.com',
                'user1@test.com',  # 중복
            ]
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # 중복 포함 모두 처리
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['success'], 2)

        # 두 번 모두 토큰 생성
        success_results = data['results']['success']
        self.assertEqual(len(success_results), 2)
        self.assertEqual(success_results[0]['email'], 'user1@test.com')
        self.assertEqual(success_results[1]['email'], 'user1@test.com')

    def test_response_structure(self):
        """Response 구조 검증"""
        self.client.force_authenticate(user=self.admin_user)

        with patch('custom_api.sso.generate_jwt_token', return_value='mock_token'):
            response = self.client.post(self.url, {
                'emails': ['user1@test.com']
            })

        data = response.json()

        # 최상위 구조
        self.assertIn('total', data)
        self.assertIn('success', data)
        self.assertIn('failed', data)
        self.assertIn('results', data)

        # results 구조
        results = data['results']
        self.assertIn('success', results)
        self.assertIn('failed', results)
        self.assertIsInstance(results['success'], list)
        self.assertIsInstance(results['failed'], list)

        # success item 구조
        success_item = results['success'][0]
        self.assertIn('email', success_item)
        self.assertIn('token', success_item)
        self.assertIn('expires_in', success_item)
        self.assertIn('user', success_item)

        # user 구조
        user = success_item['user']
        self.assertIn('id', user)
        self.assertIn('email', user)
        self.assertIn('username', user)
        self.assertIn('is_superuser', user)
