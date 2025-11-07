"""
Custom SSO Token API

사용자 존재 여부를 먼저 검증한 후 JWT 토큰을 발급합니다.
"""

import time
import jwt
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser

User = get_user_model()


def generate_jwt_token(user, expiry_seconds=600):
    """
    JWT 토큰 생성 헬퍼 함수

    label-studio-sso의 토큰 생성 로직과 동일하게 구현
    """
    payload = {
        "user_id": user.id,
        "email": user.email,
        "iat": int(time.time()),
        "exp": int(time.time()) + expiry_seconds,
        "iss": "label-studio",
        "aud": "label-studio-sso",
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


class ValidatedSSOTokenAPI(APIView):
    """
    사용자 존재 여부를 검증한 후 SSO JWT 토큰을 발급하는 API

    POST /api/custom/sso/token

    권한: Admin 사용자만 접근 가능 (누비슨 Backend API가 호출)

    Request Body:
    {
        "email": "user@example.com"
    }

    Success Response (200):
    {
        "token": "eyJhbGc...",
        "expires_in": 600,
        "user": {
            "id": 123,
            "email": "user@example.com",
            "username": "user",
            "is_superuser": false
        }
    }

    Error Response (404):
    {
        "success": false,
        "error": "User not found",
        "error_code": "USER_NOT_FOUND",
        "email": "user@example.com"
    }

    Error Response (400):
    {
        "success": false,
        "error": "email is required",
        "error_code": "INVALID_REQUEST"
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        # 이메일 검증
        email = request.data.get('email')

        if not email:
            return Response(
                {
                    'success': False,
                    'error': 'email is required',
                    'error_code': 'INVALID_REQUEST'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 사용자 존재 여부 확인
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 422 Unprocessable Entity 사용 (404는 Django가 HTML로 렌더링함)
            return Response(
                {
                    'success': False,
                    'error': f'User not found: {email}',
                    'error_code': 'USER_NOT_FOUND',
                    'email': email
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        # 사용자가 비활성화된 경우
        if not user.is_active:
            return Response(
                {
                    'success': False,
                    'error': f'User is inactive: {email}',
                    'error_code': 'USER_INACTIVE',
                    'email': email
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # JWT 토큰 생성
        try:
            token_expiry = getattr(settings, 'SSO_TOKEN_EXPIRY', 600)
            token = generate_jwt_token(user, expiry_seconds=token_expiry)

            # 성공 응답
            return Response(
                {
                    'token': token,
                    'expires_in': token_expiry,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'is_superuser': user.is_superuser,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    }
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_code': 'INTERNAL_ERROR'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchValidateSSOTokenAPI(APIView):
    """
    여러 사용자의 SSO JWT 토큰을 한 번에 발급하는 API

    POST /api/custom/sso/batch-token

    권한: Admin 사용자만 접근 가능

    Request Body:
    {
        "emails": ["user1@example.com", "user2@example.com", "user3@example.com"]
    }

    Response:
    {
        "success": true,
        "tokens": [
            {
                "email": "user1@example.com",
                "token": "eyJhbGc...",
                "expires_in": 600,
                "user_id": 1
            },
            {
                "email": "user2@example.com",
                "token": "eyJhbGc...",
                "expires_in": 600,
                "user_id": 2
            }
        ],
        "errors": [
            {
                "email": "user3@example.com",
                "error": "User not found",
                "error_code": "USER_NOT_FOUND"
            }
        ],
        "summary": {
            "total": 3,
            "success": 2,
            "failed": 1
        }
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            emails = request.data.get('emails', [])

            if not emails or not isinstance(emails, list):
                return Response(
                    {
                        'success': False,
                        'error': 'emails must be a non-empty array',
                        'error_code': 'INVALID_REQUEST'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            tokens = []
            errors = []
            token_expiry = getattr(settings, 'SSO_TOKEN_EXPIRY', 600)

            for email in emails:
                try:
                    user = User.objects.get(email=email)

                    if not user.is_active:
                        errors.append({
                            'email': email,
                            'error': 'User is inactive',
                            'error_code': 'USER_INACTIVE'
                        })
                        continue

                    token = generate_jwt_token(user, expiry_seconds=token_expiry)
                    tokens.append({
                        'email': email,
                        'token': token,
                        'expires_in': token_expiry,
                        'user_id': user.id
                    })

                except User.DoesNotExist:
                    errors.append({
                        'email': email,
                        'error': 'User not found',
                        'error_code': 'USER_NOT_FOUND'
                    })

            return Response(
                {
                    'success': True,
                    'tokens': tokens,
                    'errors': errors,
                    'summary': {
                        'total': len(emails),
                        'success': len(tokens),
                        'failed': len(errors)
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_code': 'INTERNAL_ERROR'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
