"""
Custom Export API

Label Studio 1.20.0 기반 커스텀 Export API
MLOps 시스템의 모델 학습 및 성능 계산을 위한 필터링된 Task Export 제공
"""

from django.db.models import Q, Prefetch
from django.db.models.functions import Cast
from django.db.models import DateTimeField as ModelDateTimeField
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from projects.models import Project
from tasks.models import Task, Annotation, Prediction

# Label Studio 오리지널 Serializer 사용
from tasks.serializers import PredictionSerializer, AnnotationSerializer

from .export_serializers import (
    CustomExportRequestSerializer,
    CustomExportResponseSerializer,
    TaskExportSerializer,
)


class CustomExportAPI(APIView):
    """
    Custom Export API

    MLOps 시스템에서 모델 학습 및 성능 계산을 위한 Task Export API

    Features:
    - 날짜 범위 필터링 (task.data.source_created_dt)
    - 모델 버전 필터링 (prediction.model_version)
    - 승인자 필터링 (annotation.completed_by)
    - 선택적 페이징 지원

    URL: POST /api/custom/export/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        필터링된 Task 목록 Export

        Request Body:
        {
            "project_id": 1,                        // 필수
            "search_from": "2025-01-01 00:00:00",  // 옵션
            "search_to": "2025-01-31 23:59:59",    // 옵션
            "model_version": "bert-v1",            // 옵션
            "confirm_user_id": 8,                   // 옵션
            "page": 1,                              // 옵션
            "page_size": 100                        // 옵션
        }

        Response:
        {
            "total": 150,
            "tasks": [...]
        }
        """
        # 1. Request 유효성 검증
        serializer = CustomExportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request parameters", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data

        # 2. 파라미터 추출
        project_id = validated_data['project_id']
        search_from = validated_data.get('search_from')
        search_to = validated_data.get('search_to')
        model_version = validated_data.get('model_version')
        confirm_user_id = validated_data.get('confirm_user_id')
        page = validated_data.get('page')
        page_size = validated_data.get('page_size')

        # 3. 프로젝트 존재 여부 확인
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": f"Project with id {project_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. QuerySet 빌드
        queryset = self._build_queryset(
            project_id=project_id,
            search_from=search_from,
            search_to=search_to,
            model_version=model_version,
            confirm_user_id=confirm_user_id
        )

        # 5. 전체 개수 계산
        total = queryset.count()

        # 6. 페이징 처리
        if page and page_size:
            # 페이징 적용
            start = (page - 1) * page_size
            end = start + page_size
            tasks = queryset[start:end]

            total_pages = (total + page_size - 1) // page_size
            has_next = page * page_size < total
            has_previous = page > 1

            response_data = {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "tasks": self._serialize_tasks(tasks)
            }
        else:
            # 전체 반환
            tasks = queryset.all()

            response_data = {
                "total": total,
                "tasks": self._serialize_tasks(tasks)
            }

        return Response(response_data, status=status.HTTP_200_OK)

    def _build_queryset(self, project_id, search_from, search_to, model_version, confirm_user_id):
        """
        필터 조건에 따라 QuerySet 빌드

        Args:
            project_id: 프로젝트 ID
            search_from: 검색 시작일 (task.data.source_created_dt)
            search_to: 검색 종료일 (task.data.source_created_dt)
            model_version: 모델 버전 (prediction.model_version)
            confirm_user_id: 승인자 ID (annotation.completed_by)

        Returns:
            QuerySet: 필터링된 Task QuerySet
        """
        # 기본 필터: project_id
        queryset = Task.objects.filter(project_id=project_id)

        # 날짜 범위 필터 (task.data->>'source_created_dt')
        # PostgreSQL JSONField에서 날짜 문자열을 비교하기 위해
        # timestamptz로 변환하여 타임존을 고려한 비교 수행
        if search_from:
            # Django의 DateTimeField는 timezone-aware datetime 반환
            # UTC로 변환하여 ISO 8601 형식 문자열로 저장
            # PostgreSQL의 timestamptz는 타임존을 자동으로 처리
            search_from_str = search_from.isoformat()
            queryset = queryset.extra(
                where=["(data->>'source_created_dt')::timestamptz >= %s::timestamptz"],
                params=[search_from_str]
            )

        if search_to:
            search_to_str = search_to.isoformat()
            queryset = queryset.extra(
                where=["(data->>'source_created_dt')::timestamptz <= %s::timestamptz"],
                params=[search_to_str]
            )

        # 모델 버전 필터 (prediction.model_version)
        if model_version:
            queryset = queryset.filter(
                predictions__model_version=model_version
            ).distinct()

        # 승인자 필터 (annotation.completed_by)
        # Super User만 승인자로 간주
        if confirm_user_id:
            queryset = queryset.filter(
                annotations__completed_by_id=confirm_user_id,
                annotations__completed_by__is_superuser=True
            ).distinct()

        # Prefetch 최적화: N+1 쿼리 방지
        queryset = queryset.prefetch_related(
            Prefetch(
                'annotations',
                queryset=Annotation.objects.select_related('completed_by').order_by('-created_at')
            ),
            Prefetch(
                'predictions',
                queryset=Prediction.objects.order_by('-created_at')
            )
        ).select_related('project')

        # 정렬: 최신 Task 우선
        queryset = queryset.order_by('-created_at')

        return queryset

    def _serialize_tasks(self, tasks):
        """
        Task 목록을 직렬화 (Label Studio 오리지널 Serializer 사용)

        Args:
            tasks: Task QuerySet

        Returns:
            list: 직렬화된 Task 목록
        """
        tasks_data = []

        for task in tasks:
            # Predictions 직렬화 - Label Studio 오리지널 Serializer 사용
            predictions_data = PredictionSerializer(
                task.predictions.all(),
                many=True,
                read_only=True
            ).data

            # Annotations 직렬화 - Label Studio 오리지널 Serializer 사용
            annotations = task.annotations.all()
            annotations_data = AnnotationSerializer(
                annotations,
                many=True,
                read_only=True
            ).data

            # completed_by_info 추가 (MLOps 요구사항: Webhook enrichment와 동일)
            for i, annotation in enumerate(annotations):
                if annotation.completed_by:
                    annotations_data[i]['completed_by_info'] = {
                        'id': annotation.completed_by.id,
                        'email': annotation.completed_by.email,
                        'username': annotation.completed_by.username,
                        'is_superuser': annotation.completed_by.is_superuser,
                    }

            # Task 직렬화
            task_data = {
                'id': task.id,
                'project_id': task.project_id,
                'data': task.data,
                'meta': task.meta if hasattr(task, 'meta') and task.meta else {},
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'is_labeled': task.is_labeled,
                'annotations': annotations_data,
                'predictions': predictions_data,
            }

            tasks_data.append(task_data)

        return tasks_data
