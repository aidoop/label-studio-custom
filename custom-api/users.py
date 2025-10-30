"""
Custom User API for email modification support.

This module provides user management endpoints that allow email updates,
which is required for Nubison system integration where user emails can change.
"""

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import User
from users.serializers import BaseUserSerializer


class UserUpdateSerializer(BaseUserSerializer):
    """
    User serializer that allows email modification.

    Usage:
        PATCH /api/users/{id}/
        {
            "email": "new_email@example.com",
            "first_name": "Updated Name"
        }

    Note:
        - Admins can update any user
        - Users can only update themselves
    """
    class Meta(BaseUserSerializer.Meta):
        # Remove email from read_only_fields to allow updates
        read_only_fields = ()  # Allow all fields to be updated


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_detail(request, pk):
    """
    Get or update user details.

    GET /api/users/{id}/
        Returns user details

    PATCH /api/users/{id}/
        Updates user details (email modification allowed)

    Permissions:
        - Admins can access/update any user
        - Users can only access/update themselves
    """
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Permission check: admin or self
    if not (request.user.is_staff or request.user.id == user.id):
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == 'GET':
        # Return user details
        serializer = BaseUserSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        # Update user details (including email)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            # Check email uniqueness if email is being changed
            if 'email' in request.data:
                new_email = request.data['email']
                if new_email != user.email:
                    # Check if new email already exists
                    if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                        return Response(
                            {'error': 'Email already exists'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_by_email(request):
    """
    Get user by email.

    GET /api/users/by-email/?email={email}
        Returns user details for the given email

    Permissions:
        - Admins only

    Use case:
        - Find user_id by formatted email before JWT token issuance
    """
    if not request.user.is_staff:
        return Response(
            {'error': 'Admin privileges required'},
            status=status.HTTP_403_FORBIDDEN
        )

    email = request.query_params.get('email')
    if not email:
        return Response(
            {'error': 'Email parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(email=email)
        serializer = BaseUserSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
