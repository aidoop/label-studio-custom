"""
Custom Permission Mixins

Provides mixins to add custom permissions to existing views.
"""

from custom_permissions.permissions import IsAnnotationOwnerOrReadOnly


class AnnotationOwnershipMixin:
    """
    Mixin to add annotation ownership permission to existing views.

    This mixin adds the IsAnnotationOwnerOrReadOnly permission to the view's
    permission_classes, ensuring that only annotation owners (or admins) can
    edit/delete annotations.

    Usage:
        class CustomAnnotationAPI(AnnotationOwnershipMixin, AnnotationAPI):
            pass
    """

    def get_permissions(self):
        """
        Add custom annotation ownership permission to existing permissions.

        Returns:
            list: List of permission instances
        """
        permissions = super().get_permissions()

        # Add annotation ownership permission
        permissions.append(IsAnnotationOwnerOrReadOnly())

        return permissions
