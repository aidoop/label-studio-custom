#!/usr/bin/env python
"""
Label Studio 초기 사용자 생성 스크립트

관리자 및 일반 사용자를 자동으로 생성합니다.
"""

import os
import sys
import django

# Django 설정 로드
sys.path.insert(0, '/label-studio')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# 생성할 사용자 목록
USERS = [
    {
        'email': 'admin@nubison.localhost',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_superuser': True,
        'is_staff': True,
    },
    {
        'email': 'user1@nubison.localhost',
        'password': 'user123',
        'first_name': 'User',
        'last_name': 'One',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'email': 'user2@nubison.localhost',
        'password': 'user123',
        'first_name': 'User',
        'last_name': 'Two',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'email': 'annotator@nubison.localhost',
        'password': 'annotator123',
        'first_name': 'Annotator',
        'last_name': 'Test',
        'is_superuser': False,
        'is_staff': False,
    },
]


def create_users():
    """사용자 생성"""
    print("=" * 60)
    print("Label Studio 초기 사용자 생성")
    print("=" * 60)
    print()

    created_count = 0
    skipped_count = 0

    for user_data in USERS:
        email = user_data['email']

        # 이미 존재하는지 확인
        if User.objects.filter(email=email).exists():
            print(f"⊗ {email} - 이미 존재함 (건너뜀)")
            skipped_count += 1
            continue

        # 사용자 생성
        password = user_data.pop('password')
        user = User.objects.create_user(**user_data)
        user.set_password(password)
        user.save()

        role = "관리자" if user.is_superuser else "일반 사용자"
        print(f"✓ {email} - {role} 생성 완료")
        created_count += 1

    print()
    print("=" * 60)
    print(f"완료: {created_count}명 생성, {skipped_count}명 건너뜀")
    print("=" * 60)
    print()

    # 사용자 정보 출력
    if created_count > 0:
        print("생성된 계정 정보:")
        print("-" * 60)
        for user_data in USERS:
            email = user_data['email']
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                role = "관리자" if user.is_superuser else "일반 사용자"
                # 비밀번호는 원본 USERS 딕셔너리에서 가져오기
                for original in USERS:
                    if original['email'] == email:
                        password = original.get('password', '(설정됨)')
                        break
                print(f"  Email: {email}")
                print(f"  Role:  {role}")
                print(f"  Password: {password}")
                print("-" * 60)


if __name__ == '__main__':
    try:
        create_users()
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
