"""
Custom Export API Serializers

Label Studio 1.20.0 기반 커스텀 Export API의 Request/Response Serializer
"""

from rest_framework import serializers


class CustomExportRequestSerializer(serializers.Serializer):
    """
    Custom Export API Request Serializer

    MLOps 시스템에서 모델 학습 및 성능 계산을 위한 필터링된 Export 요청
    """

    # 필수 필드
    project_id = serializers.IntegerField(
        required=True,
        help_text="Label Studio 프로젝트 ID"
    )

    # 선택 필드 - 날짜 범위 필터
    search_from = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="검색 시작일 (format: yyyy-mm-dd hh:mi:ss 또는 ISO 8601) - task.data의 날짜 필드 기준"
    )

    search_to = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="검색 종료일 (format: yyyy-mm-dd hh:mi:ss 또는 ISO 8601) - task.data의 날짜 필드 기준"
    )

    search_date_field = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default='source_created_at',
        help_text="검색할 날짜 필드명 (task.data 내의 필드명, 기본값: source_created_at)"
    )

    def validate_search_date_field(self, value):
        """
        search_date_field 필드명 검증 (SQL Injection 방지)

        영문자, 숫자, 언더스코어만 허용
        """
        if not value:
            return 'source_created_at'

        # 안전한 필드명 패턴: 영문자, 숫자, 언더스코어만 허용
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', value):
            raise serializers.ValidationError(
                "필드명은 영문자, 숫자, 언더스코어(_)만 사용 가능합니다. "
                "첫 글자는 영문자 또는 언더스코어여야 합니다."
            )

        # 필드명 길이 제한 (최대 64자)
        if len(value) > 64:
            raise serializers.ValidationError(
                "필드명은 최대 64자까지 입력 가능합니다."
            )

        return value

    # 선택 필드 - 모델 버전 필터
    model_version = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="추론 모델 버전 - prediction.model_version 기준"
    )

    # 선택 필드 - 승인자 필터
    confirm_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="라벨링 승인자 User ID - annotation.completed_by 기준 (Super User)"
    )

    # 선택 필드 - 페이징
    page = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="페이지 번호 (1부터 시작, 없으면 전체 반환)"
    )

    page_size = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=10000,
        help_text="페이지당 Task 개수 (최대 10000, 없으면 전체 반환)"
    )

    def validate(self, data):
        """
        필드 간 유효성 검증
        """
        # page와 page_size는 함께 제공되어야 함
        page = data.get('page')
        page_size = data.get('page_size')

        if (page is not None) != (page_size is not None):
            raise serializers.ValidationError(
                "page와 page_size는 함께 제공되어야 합니다."
            )

        return data


class AnnotationSerializer(serializers.Serializer):
    """
    Annotation 정보 직렬화
    """
    id = serializers.IntegerField()
    completed_by = serializers.IntegerField(allow_null=True)
    completed_by_info = serializers.DictField(required=False)
    result = serializers.JSONField()
    was_cancelled = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class PredictionSerializer(serializers.Serializer):
    """
    Prediction 정보 직렬화
    """
    id = serializers.IntegerField()
    model_version = serializers.CharField(allow_blank=True, allow_null=True)
    score = serializers.FloatField(allow_null=True)
    result = serializers.JSONField()
    created_at = serializers.DateTimeField()


class TaskExportSerializer(serializers.Serializer):
    """
    Export된 Task 정보 직렬화
    """
    id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    data = serializers.JSONField()
    meta = serializers.JSONField(required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    is_labeled = serializers.BooleanField()
    annotations = AnnotationSerializer(many=True)
    predictions = PredictionSerializer(many=True)


class CustomExportResponseSerializer(serializers.Serializer):
    """
    Custom Export API Response Serializer
    """
    total = serializers.IntegerField(
        help_text="필터링된 전체 Task 개수"
    )

    page = serializers.IntegerField(
        required=False,
        help_text="현재 페이지 번호 (페이징 사용 시)"
    )

    page_size = serializers.IntegerField(
        required=False,
        help_text="페이지당 Task 개수 (페이징 사용 시)"
    )

    total_pages = serializers.IntegerField(
        required=False,
        help_text="전체 페이지 수 (페이징 사용 시)"
    )

    has_next = serializers.BooleanField(
        required=False,
        help_text="다음 페이지 존재 여부 (페이징 사용 시)"
    )

    has_previous = serializers.BooleanField(
        required=False,
        help_text="이전 페이지 존재 여부 (페이징 사용 시)"
    )

    tasks = TaskExportSerializer(many=True)
