#!/usr/bin/env python3
"""
Webhook Payload Enrichment Patch for Label Studio

이 스크립트는 Label Studio의 webhooks/utils.py 파일을 패치하여
annotation webhook payload에 completed_by_info 필드를 추가합니다.

추가되는 필드:
- completed_by_info.id: 사용자 ID
- completed_by_info.email: 사용자 이메일
- completed_by_info.username: 사용자명
- completed_by_info.is_superuser: 수퍼유저 여부

사용 목적:
MLOps 시나리오에서 annotation 이벤트를 수신할 때, 생성한 사용자가
superuser인지 일반 사용자인지 구분하여 모델 성능 측정에 활용합니다.
- Superuser의 annotation: 모델 성능 측정에 사용
- Regular user의 annotation: 무시 (또는 반대 정책)
"""
import sys

def patch_webhooks():
    """
    Label Studio의 webhooks/utils.py 파일의 run_webhook_sync 함수에
    completed_by_info 추가 로직을 삽입합니다.
    """
    try:
        webhooks_utils_path = "/label-studio/label_studio/webhooks/utils.py"

        # Read the original file
        with open(webhooks_utils_path, 'r') as f:
            content = f.read()

        # Define the injection point (run_webhook_sync 함수 시작 부분)
        injection_point = '''def run_webhook_sync(webhook, action, payload=None):
    """Run one webhook for action.

    This function must not raise any exceptions.
    """
'''

        # Define the enrichment code to inject
        # annotation 관련 이벤트의 경우 completed_by_info 필드 추가
        enrichment_code = '''    # === CUSTOM: Add completed_by_info to annotation payloads ===
    # Annotation 이벤트인 경우 사용자 정보를 추가합니다
    if action in ['ANNOTATION_CREATED', 'ANNOTATION_UPDATED', 'ANNOTATIONS_DELETED'] and payload:
        try:
            if 'annotation' in payload and 'completed_by' in payload['annotation']:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user_id = payload['annotation']['completed_by']
                try:
                    user = User.objects.get(id=user_id)
                    payload['annotation']['completed_by_info'] = {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'is_superuser': user.is_superuser,
                    }
                except User.DoesNotExist:
                    pass  # 사용자가 없는 경우 무시
        except Exception:
            pass  # 에러 발생 시 무시 (webhook 전송은 계속)
    # === END CUSTOM PATCH ===

'''

        # Apply the patch
        if injection_point in content:
            content = content.replace(injection_point, injection_point + enrichment_code)
            with open(webhooks_utils_path, 'w') as f:
                f.write(content)
            print("[PATCH] ✅ Successfully patched webhooks/utils.py")
            print("[PATCH]    Added completed_by_info enrichment to annotation webhooks")
            sys.exit(0)
        else:
            print("[PATCH] ⚠️  Could not find injection point in webhooks/utils.py")
            print("[PATCH]    run_webhook_sync function signature may have changed")
            sys.exit(1)

    except Exception as e:
        print(f"[PATCH] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    patch_webhooks()
