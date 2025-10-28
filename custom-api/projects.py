"""
Custom Project API

ProjectSerializer의 model_version 필드 유효성 검증을 우회합니다.
MLOps 시스템의 외부 모델 버전 ID를 저장하기 위해 필요합니다.

Issue:
- Project 생성 시: model_version 유효성 체크 안함 (정상)
- Project 수정 시: model_version 유효성 체크 함 (문제)
  Error: "Model version doesn't exist either as live model or as static predictions."

Solution:
- validate_model_version 메서드를 오버라이드하여 유효성 검증을 skip
"""

from rest_framework import serializers
from projects.serializers import ProjectSerializer as BaseProjectSerializer
from projects.api import ProjectAPI as BaseProjectAPI


class ProjectSerializer(BaseProjectSerializer):
    """
    Custom ProjectSerializer with model_version validation bypass.

    Original behavior (Label Studio 1.20.0):
    - validate_model_version() checks if model_version exists in:
      1. ML backends (p.ml_backends.filter(title=value))
      2. Static predictions (p.predictions.filter(project=p, model_version=value))
    - Raises ValidationError if not found

    Custom behavior:
    - Always accepts any model_version value
    - Allows storing external MLOps system model version IDs
    - Maintains consistency with Project creation behavior (no validation)
    """

    def validate_model_version(self, value):
        """
        Override model_version validation to skip existence checks.

        Original validation logic (lines 262-279 in projects/serializers.py):
        ```python
        def validate_model_version(self, value):
            p = self.instance

            if p is not None and p.model_version != value and value != '':
                if p.ml_backends.filter(title=value).union(
                    p.predictions.filter(project=p, model_version=value)
                ).exists():
                    return value
                else:
                    raise serializers.ValidationError(
                        "Model version doesn't exist either as live model or as static predictions."
                    )

            return value
        ```

        Custom logic:
        - Simply return the value without validation
        - Allows any string value to be stored

        Args:
            value (str): The model_version value to validate

        Returns:
            str: The unchanged value
        """
        # Skip validation, just return the value
        return value


class ProjectAPI(BaseProjectAPI):
    """
    Custom ProjectAPI using the custom ProjectSerializer.

    This ensures that PATCH requests to /api/projects/{id}/ use our
    custom serializer with bypassed model_version validation.

    Usage:
    - PATCH http://localhost:8080/api/projects/11/
    - Body: {"model_version": "aiver03"}
    - Result: Success (no validation error)
    """

    serializer_class = ProjectSerializer
