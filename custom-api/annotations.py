"""
Custom Annotation API

AnnotationAPI에 AnnotationOwnershipMixin을 적용하여
사용자가 자신이 작성한 annotation만 수정/삭제할 수 있도록 제한합니다.
"""

from tasks.api import AnnotationAPI as BaseAnnotationAPI
from custom_permissions.mixins import AnnotationOwnershipMixin


class AnnotationAPI(AnnotationOwnershipMixin, BaseAnnotationAPI):
    """
    Annotation API with custom ownership permissions.

    Custom modification: Added AnnotationOwnershipMixin to enforce that
    users can only edit/delete their own annotations (admins can edit all).

    Rules:
    - Read operations (GET): All authenticated users
    - Create operations (POST): All authenticated users
    - Update/Delete operations (PUT, PATCH, DELETE): Only annotation owner or admins
    """
    pass
