from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class NotificationType(models.TextChoices):
    PRODUCT_ASSIGNED = 'PRODUCT_ASSIGNED', _('Product Assigned')
    STAGE_COMPLETED = 'STAGE_COMPLETED', _('Stage Completed')
    APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', _('Approval Required')
    PRODUCT_REJECTED = 'PRODUCT_REJECTED', _('Product Rejected')
    INSPECTION_FAILED = 'INSPECTION_FAILED', _('Inspection Failed')
    DOCUMENT_UPDATED = 'DOCUMENT_UPDATED', _('Document Updated')
    READY_FOR_NEXT_STAGE = 'READY_FOR_NEXT_STAGE', _('Ready for Next Stage')
    READY_FOR_DISPATCH = 'READY_FOR_DISPATCH', _('Ready for Dispatch')
    SYSTEM = 'SYSTEM', _('System Alert')

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
