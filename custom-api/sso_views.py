"""
SSO 전용 로그인 뷰

iframe 통합 시에는 SSO 전용 메시지를 표시하고,
일반 브라우저 접근 시에는 원래 로그인 페이지로 이동합니다.
"""

from django.shortcuts import render


def sso_login_required(request):
    """
    조건부 로그인 페이지

    동작 방식:
    - iframe 환경: SSO 전용 안내 페이지
    - 일반 브라우저: 원래 Label Studio 로그인 폼

    iframe 감지: hideHeader=true 파라미터 사용
    """
    # iframe 환경 감지 (hideHeader 파라미터)
    is_iframe = request.GET.get('hideHeader') == 'true'

    if is_iframe:
        # iframe 환경: SSO 전용 안내 페이지
        return render(request, 'sso_login.html')
    else:
        # 일반 브라우저: 원래 Label Studio 로그인 뷰
        from users.views import user_login
        return user_login(request)
