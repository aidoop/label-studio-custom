"""
Custom Signals for Label Studio

자동화 기능:
- OrganizationMember 생성 시 active_organization 자동 설정
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from organizations.models import OrganizationMember

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OrganizationMember)
def set_active_organization_on_membership(sender, instance, created, **kwargs):
    """
    OrganizationMember 생성 시 사용자의 active_organization 자동 설정

    사용자가 Organization에 처음 추가될 때:
    - active_organization이 None인 경우 → 자동으로 해당 organization 설정
    - 이미 active_organization이 있는 경우 → 변경하지 않음

    Args:
        sender: OrganizationMember 모델 클래스
        instance: 생성/업데이트된 OrganizationMember 인스턴스
        created: True if new instance was created
        **kwargs: 추가 인자
    """
    if created:
        user = instance.user
        organization = instance.organization

        # active_organization이 None인 경우에만 설정
        if user.active_organization is None:
            user.active_organization = organization
            user.save(update_fields=['active_organization'])

            logger.info(
                f"[Auto-Set active_organization] User '{user.email}' "
                f"→ Organization '{organization.title}' (ID: {organization.id})"
            )
            print(
                f"[Signal] Set active_organization for {user.email} "
                f"→ {organization.title}"
            )
