"""
Tests for Custom Permissions

Test cases for IsAnnotationOwnerOrReadOnly permission class.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from unittest.mock import Mock

from custom_permissions.permissions import IsAnnotationOwnerOrReadOnly

User = get_user_model()


class IsAnnotationOwnerOrReadOnlyTests(TestCase):
    """Test cases for IsAnnotationOwnerOrReadOnly permission"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = APIRequestFactory()
        self.permission = IsAnnotationOwnerOrReadOnly()

        # Create test users
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            email='superuser@example.com',
            password='testpass123'
        )

    def _create_mock_annotation(self, completed_by=None):
        """Create a mock annotation object"""
        annotation = Mock()
        annotation.id = 1
        annotation.completed_by = completed_by
        annotation.project = None
        return annotation

    def test_has_permission_unauthenticated(self):
        """Unauthenticated users should not have permission"""
        request = self.factory.get('/api/annotations/')
        request.user = None

        result = self.permission.has_permission(request, None)
        self.assertFalse(result)

    def test_has_permission_authenticated_get(self):
        """Authenticated users can perform GET requests"""
        request = self.factory.get('/api/annotations/')
        request.user = self.owner

        result = self.permission.has_permission(request, None)
        self.assertTrue(result)

    def test_has_permission_authenticated_post(self):
        """Authenticated users can perform POST requests"""
        request = self.factory.post('/api/annotations/')
        request.user = self.owner

        result = self.permission.has_permission(request, None)
        self.assertTrue(result)

    def test_has_object_permission_owner_can_edit(self):
        """Annotation owner can edit their own annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.patch(f'/api/annotations/{annotation.id}/')
        request.user = self.owner

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)

    def test_has_object_permission_owner_can_delete(self):
        """Annotation owner can delete their own annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.delete(f'/api/annotations/{annotation.id}/')
        request.user = self.owner

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)

    def test_has_object_permission_other_user_cannot_edit(self):
        """Other users cannot edit someone else's annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.patch(f'/api/annotations/{annotation.id}/')
        request.user = self.other_user

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertFalse(result)

    def test_has_object_permission_other_user_cannot_delete(self):
        """Other users cannot delete someone else's annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.delete(f'/api/annotations/{annotation.id}/')
        request.user = self.other_user

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertFalse(result)

    def test_has_object_permission_other_user_can_read(self):
        """Other users can read someone else's annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.get(f'/api/annotations/{annotation.id}/')
        request.user = self.other_user

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)

    def test_has_object_permission_admin_can_edit(self):
        """Admin users can edit any annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.patch(f'/api/annotations/{annotation.id}/')
        request.user = self.admin_user

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)

    def test_has_object_permission_superuser_can_edit(self):
        """Superusers can edit any annotation"""
        annotation = self._create_mock_annotation(completed_by=self.owner)
        request = self.factory.patch(f'/api/annotations/{annotation.id}/')
        request.user = self.superuser

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)

    def test_has_object_permission_annotation_without_owner(self):
        """Annotations without owner can be edited by anyone"""
        annotation = self._create_mock_annotation(completed_by=None)
        request = self.factory.patch(f'/api/annotations/{annotation.id}/')
        request.user = self.other_user

        result = self.permission.has_object_permission(request, None, annotation)
        self.assertTrue(result)
