"""
Custom Admin User Management API

Admin 사용자만 접근 가능한 사용자 관리 API를 제공합니다.
- Superuser 생성
- 일반 사용자를 Superuser로 승격
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.authtoken.models import Token
from organizations.models import Organization, OrganizationMember

User = get_user_model()


class CreateSuperuserAPI(APIView):
    """
    Superuser 생성 API

    POST /api/admin/users/create-superuser

    권한: Admin 사용자만 접근 가능

    Request Body:
    {
        "email": "newadmin@example.com",
        "username": "newadmin",  (optional, defaults to email)
        "password": "secure_password123",
        "first_name": "Admin",  (optional)
        "last_name": "User",  (optional)
        "create_token": true,  (optional, defaults to true)
        "add_to_organization": 1  (optional, defaults to creator's active_organization)
    }

    Organization 자동 할당:
    - add_to_organization이 지정되지 않으면 → 생성자의 active_organization에 자동 추가
    - 명시적으로 지정하면 → 지정된 organization에 추가
    - 생성자에게 active_organization이 없으면 → organization 추가 안 됨

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "email": "newadmin@example.com",
            "username": "newadmin",
            "is_superuser": true,
            "is_staff": true,
            "is_active": true
        },
        "token": "abc123...",  (if create_token=true)
        "organization": {  (if user was added to organization)
            "id": 1,
            "title": "Default Organization"
        }
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            # 필수 필드 검증
            email = request.data.get('email')
            password = request.data.get('password')

            if not email:
                return Response(
                    {'success': False, 'error': 'email is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not password:
                return Response(
                    {'success': False, 'error': 'password is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 이미 존재하는 사용자 확인
            if User.objects.filter(email=email).exists():
                return Response(
                    {'success': False, 'error': f'User with email {email} already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 선택적 필드
            username = request.data.get('username', email)
            first_name = request.data.get('first_name', '')
            last_name = request.data.get('last_name', '')
            create_token = request.data.get('create_token', True)
            org_id = request.data.get('add_to_organization')

            # Organization ID 기본값 설정: 생성자의 active_organization 사용
            if org_id is None and request.user.active_organization:
                org_id = request.user.active_organization.id

            # Superuser 생성
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()

            # 응답 데이터 구성
            response_data = {
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                }
            }

            # API 토큰 생성 (선택사항)
            if create_token:
                token, _ = Token.objects.get_or_create(user=user)
                response_data['token'] = token.key

            # Organization에 추가 (선택사항)
            if org_id:
                try:
                    org = Organization.objects.get(pk=org_id)
                    OrganizationMember.objects.get_or_create(
                        user=user,
                        organization=org
                    )
                    response_data['organization'] = {
                        'id': org.id,
                        'title': org.title,
                    }
                except Organization.DoesNotExist:
                    response_data['warning'] = f'Organization with ID {org_id} not found'

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PromoteToSuperuserAPI(APIView):
    """
    기존 사용자를 Superuser로 승격

    POST /api/admin/users/<user_id>/promote-to-superuser

    권한: Admin 사용자만 접근 가능

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "is_superuser": true,
            "is_staff": true
        }
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            # 사용자 조회
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {'success': False, 'error': f'User with ID {user_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 이미 superuser인 경우
            if user.is_superuser:
                return Response(
                    {'success': False, 'error': f'User {user.email} is already a superuser'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Superuser로 승격
            user.is_superuser = True
            user.is_staff = True
            user.save()

            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DemoteFromSuperuserAPI(APIView):
    """
    Superuser 권한 해제

    POST /api/admin/users/<user_id>/demote-from-superuser

    권한: Admin 사용자만 접근 가능

    Response:
    {
        "success": true,
        "user": {
            "id": 1,
            "email": "user@example.com",
            "is_superuser": false,
            "is_staff": false
        }
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            # 사용자 조회
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {'success': False, 'error': f'User with ID {user_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 이미 일반 사용자인 경우
            if not user.is_superuser:
                return Response(
                    {'success': False, 'error': f'User {user.email} is not a superuser'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 자기 자신을 해제하려는 경우 경고
            if user.id == request.user.id:
                return Response(
                    {'success': False, 'error': 'You cannot demote yourself from superuser'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Superuser 권한 해제
            user.is_superuser = False
            user.is_staff = False
            user.save()

            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListUsersAPI(APIView):
    """
    전체 사용자 목록 조회 (is_superuser 포함)

    GET /api/admin/users/list

    권한: Admin 사용자만 접근 가능

    Response:
    {
        "success": true,
        "count": 10,
        "users": [
            {
                "id": 1,
                "email": "user@example.com",
                "username": "user",
                "first_name": "John",
                "last_name": "Doe",
                "is_superuser": true,
                "is_staff": true,
                "is_active": true,
                "active_organization": 1
            },
            ...
        ]
    }
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            # 모든 사용자 조회
            users = User.objects.all().order_by('-id')

            # 사용자 데이터 구성
            users_data = []
            for user in users:
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                    'active_organization': user.active_organization if isinstance(user.active_organization, int) else (user.active_organization.id if user.active_organization else None),
                }
                users_data.append(user_data)

            return Response({
                'success': True,
                'count': len(users_data),
                'users': users_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
