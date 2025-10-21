#!/usr/bin/env python
"""
Label Studio 초기 사용자 및 Organization 생성 스크립트

다음을 자동으로 생성합니다:
- 관리자 및 일반 사용자
- Organization
- Organization 멤버십
- Admin API 토큰
"""

import os
import sys
import django

# Django 설정 로드
sys.path.insert(0, '/label-studio')
sys.path.insert(0, '/label-studio/label_studio')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')
django.setup()

from django.contrib.auth import get_user_model
from organizations.models import Organization, OrganizationMember
from rest_framework.authtoken.models import Token

User = get_user_model()

# 생성할 사용자 목록
USERS = [
    {
        'email': 'admin@nubison.io',
        'username': 'admin@nubison.io',
        'password': 'admin123!',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_superuser': True,
        'is_staff': True,
        'is_active': True,
    },
    {
        'email': 'annotator@nubison.io',
        'username': 'annotator@nubison.io',
        'password': 'annotator123!',
        'first_name': 'Annotator',
        'last_name': 'User',
        'is_superuser': False,
        'is_staff': False,
        'is_active': True,
    },
    {
        'email': 'manager@nubison.io',
        'username': 'manager@nubison.io',
        'password': 'manager123!',
        'first_name': 'Manager',
        'last_name': 'User',
        'is_superuser': False,
        'is_staff': False,
        'is_active': True,
    },
]


def create_users():
    """사용자 생성"""
    print("=" * 70)
    print("1. 사용자 생성")
    print("=" * 70)

    created_users = []

    for user_data in USERS:
        email = user_data['email']
        password = user_data.pop('password')

        # 이미 존재하는지 확인
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            print(f"  ⊗ {email} - 이미 존재함 (건너뜀)")
        else:
            # 사용자 생성
            user = User.objects.create(**user_data)
            user.set_password(password)
            user.save()

            role = "관리자" if user.is_superuser else "일반 사용자"
            print(f"  ✓ {email} - {role} 생성 완료")

        created_users.append(user)

    print()
    return created_users


def create_organization(admin_user):
    """Organization 생성"""
    print("=" * 70)
    print("2. Organization 생성")
    print("=" * 70)

    # Organization 생성
    org, created = Organization.objects.get_or_create(
        defaults={
            'title': 'Default Organization',
            'created_by': admin_user,
        }
    )

    if created:
        print(f"  ✓ Organization '{org.title}' 생성 완료")
    else:
        # 기존 Organization의 created_by가 None이면 설정
        if org.created_by is None:
            org.created_by = admin_user
            org.save()
            print(f"  ⊗ Organization '{org.title}' 이미 존재함 (created_by 업데이트)")
        else:
            print(f"  ⊗ Organization '{org.title}' 이미 존재함")

    print(f"  Organization ID: {org.pk}")
    print(f"  Created by: {org.created_by.email}")
    print()

    return org


def add_members_to_organization(org, users):
    """Organization에 사용자 추가"""
    print("=" * 70)
    print("3. Organization 멤버 추가")
    print("=" * 70)

    for user in users:
        member, created = OrganizationMember.objects.get_or_create(
            user=user,
            organization=org
        )

        if created:
            print(f"  ✓ {user.email} - 멤버로 추가 완료")
        else:
            print(f"  ⊗ {user.email} - 이미 멤버임")

    print(f"\n  Total members: {OrganizationMember.objects.filter(organization=org).count()}")
    print()


def create_admin_token(admin_user):
    """Admin API 토큰 생성"""
    print("=" * 70)
    print("4. Admin API 토큰 생성")
    print("=" * 70)

    token, created = Token.objects.get_or_create(user=admin_user)

    if created:
        print(f"  ✓ API 토큰 생성 완료")
    else:
        print(f"  ⊗ API 토큰 이미 존재함")

    print(f"  Token: {token.key}")
    print()
    print(f"  Backend .env 파일에 다음을 설정하세요:")
    print(f"  LABEL_STUDIO_API_TOKEN={token.key}")
    print()

    return token


def print_summary(users, org, token):
    """최종 요약 출력"""
    print("=" * 70)
    print("초기화 완료!")
    print("=" * 70)
    print()
    print("생성된 계정:")
    print("-" * 70)

    for user_data in USERS:
        email = user_data['email']
        user = User.objects.get(email=email)
        role = "관리자" if user.is_superuser else "일반 사용자"

        # 원본 비밀번호 찾기
        password = '(설정됨)'
        for original in USERS:
            if original['email'] == email:
                password = original.get('password', '(설정됨)')
                break

        print(f"  Email:    {email}")
        print(f"  Password: {password}")
        print(f"  Role:     {role}")
        print("-" * 70)

    print()
    print(f"Organization: {org.title} (ID: {org.pk})")
    print(f"Total users: {len(users)}")
    print(f"Admin API Token: {token.key}")
    print()


def main():
    try:
        print()
        print("=" * 70)
        print("Label Studio 초기화 시작")
        print("=" * 70)
        print()

        # 1. 사용자 생성
        users = create_users()

        # Admin 사용자 찾기
        admin_user = None
        for user in users:
            if user.is_superuser:
                admin_user = user
                break

        if not admin_user:
            raise Exception("Admin 사용자를 찾을 수 없습니다!")

        # 2. Organization 생성
        org = create_organization(admin_user)

        # 3. Organization 멤버 추가
        add_members_to_organization(org, users)

        # 4. Admin API 토큰 생성
        token = create_admin_token(admin_user)

        # 5. 요약 출력
        print_summary(users, org, token)

        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print("오류 발생!")
        print("=" * 70)
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
