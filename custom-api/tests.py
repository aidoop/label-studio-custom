"""
Custom Export API Tests

Label Studio 1.20.0 기반 커스텀 Export API 테스트
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
