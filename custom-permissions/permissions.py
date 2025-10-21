"""
Custom Permission Classes

Provides fine-grained permission control for Label Studio resources,
particularly for annotations.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
import logging

logger = logging.getLogger(__name__)


class IsAnnotationOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an annotation to edit/delete it.

    Rules:
    - Read operations (GET, HEAD, OPTIONS) are allowed for everyone
    - Create operations (POST) are allowed for authenticated users
    - Update/Delete operations (PUT, PATCH, DELETE) are only allowed for:
      - The annotation owner (completed_by)
      - Admin users (is_staff or is_superuser)
      - Organization administrators

    Usage:
        class AnnotationViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsAnnotationOwnerOrReadOnly]
    """

    message = "You can only edit or delete your own annotations."

    def has_permission(self, request, view):
        """
        Check if user has permission to access the view.

        Args:
            request: The request object
            view: The view being accessed

        Returns:
            bool: True if user has permission, False otherwise
        """
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow read operations for all authenticated users
        if request.method in SAFE_METHODS:
            return True

        # Allow create operations for authenticated users
        if request.method == 'POST':
            return True

        # For update/delete, check object-level permissions
        return True

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to perform action on specific annotation.

        Args:
            request: The request object
            view: The view being accessed
            obj: The annotation object

        Returns:
            bool: True if user has permission, False otherwise
        """
        # Allow read operations for all authenticated users
        if request.method in SAFE_METHODS:
            return True

        # Admin users can edit/delete any annotation
        if request.user.is_staff or request.user.is_superuser:
            logger.info(f"Admin user {request.user.email} accessing annotation {obj.id}")
            return True

        # Check if user is organization admin/manager
        # Label Studio uses organizations for multi-tenancy
        if hasattr(obj, 'project') and obj.project:
            project = obj.project
            if hasattr(project, 'organization') and project.organization:
                org = project.organization

                # Check if user is organization admin
                org_membership = org.members.filter(user=request.user).first()
                if org_membership:
                    # Organization owners and admins can edit any annotation
                    if org.created_by == request.user:
                        logger.info(f"Organization owner {request.user.email} accessing annotation {obj.id}")
                        return True

        # Check if user is the annotation owner
        if hasattr(obj, 'completed_by') and obj.completed_by:
            is_owner = obj.completed_by == request.user

            if not is_owner:
                logger.warning(
                    f"User {request.user.email} attempted to modify annotation {obj.id} "
                    f"owned by {obj.completed_by.email}"
                )

            return is_owner

        # If annotation has no owner, allow the action
        # (This shouldn't normally happen, but we allow it for safety)
        logger.warning(f"Annotation {obj.id} has no completed_by field")
        return True


class IsProjectMember(BasePermission):
    """
    Permission to check if user is a member of the project.

    This is a helper permission that can be combined with other permissions.
    """

    message = "You must be a member of this project."

    def has_object_permission(self, request, view, obj):
        """
        Check if user is a member of the project.

        Args:
            request: The request object
            view: The view being accessed
            obj: The object (annotation, task, etc.)

        Returns:
            bool: True if user is project member, False otherwise
        """
        # Get the project from the object
        project = None
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'task') and hasattr(obj.task, 'project'):
            project = obj.task.project

        if not project:
            return False

        # Check if user is project member
        return project.has_permission(request.user)
