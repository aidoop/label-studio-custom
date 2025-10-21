# 초기 사용자 생성 스크립트

## 📋 기본 제공 사용자

`init_users.sh` 스크립트를 실행하면 다음 사용자가 자동으로 생성됩니다:

| Email | Password | 역할 | 설명 |
|-------|----------|------|------|
| `admin@nubison.localhost` | `admin123` | 관리자 | 모든 권한 |
| `user1@nubison.localhost` | `user123` | 일반 사용자 | 프로젝트 작업 |
| `user2@nubison.localhost` | `user123` | 일반 사용자 | 프로젝트 작업 |
| `annotator@nubison.localhost` | `annotator123` | 일반 사용자 | 라벨링 작업 |

---

## 🚀 사용 방법

### 자동 생성 (권장)

```bash
# Makefile 사용
make init-users

# 또는 직접 실행
docker-compose exec labelstudio bash /scripts/init_users.sh
```

### 수동으로 Python 스크립트 실행

```bash
docker-compose exec labelstudio python /scripts/create_initial_users.py
```

---

## ✏️ 사용자 커스터마이징

`create_initial_users.py` 파일을 편집하여 사용자를 추가/수정할 수 있습니다:

```python
USERS = [
    {
        'email': 'your-email@nubison.localhost',
        'password': 'your-password',
        'first_name': 'First',
        'last_name': 'Last',
        'is_superuser': False,  # True면 관리자
        'is_staff': False,       # True면 Django admin 접근 가능
    },
    # 더 많은 사용자 추가...
]
```

---

## 🔒 보안 주의사항

⚠️ **프로덕션 환경에서는:**

1. **비밀번호 변경**: 기본 비밀번호(`admin123`, `user123` 등)를 강력한 비밀번호로 변경
2. **스크립트 제거**: 초기 설정 후 이 스크립트들을 제거하거나 비활성화
3. **환경변수 사용**: 비밀번호를 환경변수에서 읽어오도록 수정

---

## 📝 파일 설명

- **`create_initial_users.py`**: 사용자 생성 로직 (Python)
- **`init_users.sh`**: 마이그레이션 + 사용자 생성 (Bash wrapper)
- **`README.md`**: 이 파일

---

## 🔧 문제 해결

### 사용자가 이미 존재함

스크립트는 기존 사용자를 건너뛰므로 안전하게 여러 번 실행할 수 있습니다.

### 사용자 삭제 후 재생성

```bash
# Django shell 접속
docker-compose exec labelstudio python /label-studio/label_studio/manage.py shell

# 사용자 삭제
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(email='admin@nubison.localhost').delete()
exit()

# 다시 생성
make init-users
```

---

**개발 환경에서만 사용하세요!**
