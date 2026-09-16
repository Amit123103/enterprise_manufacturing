from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class AuditAction(models.TextChoices):
    LOGIN = 'LOGIN', _('Login')
    LOGOUT = 'LOGOUT', _('Logout')
    ADMIN_CREATED = 'ADMIN_CREATED', _('Admin Created')
    ADMIN_EDITED = 'ADMIN_EDITED', _('Admin Edited')
    ADMIN_SUSPENDED = 'ADMIN_SUSPENDED', _('Admin Suspended')
    ADMIN_ACTIVATED = 'ADMIN_ACTIVATED', _('Admin Activated')
    PERMISSION_CHANGED = 'PERMISSION_CHANGED', _('Permission Changed')
    USER_CREATED = 'USER_CREATED', _('User Created')
    USER_EDITED = 'USER_EDITED', _('User Edited')
    USER_SUSPENDED = 'USER_SUSPENDED', _('User Suspended')
    ROLE_CHANGED = 'ROLE_CHANGED', _('Role Changed')
    PRODUCT_CREATED = 'PRODUCT_CREATED', _('Product Created')
    PRODUCT_UPDATED = 'PRODUCT_UPDATED', _('Product Updated')
    STAGE_COMPLETED = 'STAGE_COMPLETED', _('Stage Completed')
    INSPECTION = 'INSPECTION', _('Inspection')
    APPROVAL = 'APPROVAL', _('Approval')
    REJECTION = 'REJECTION', _('Rejection')
    DISPATCH = 'DISPATCH', _('Dispatch')
    DOCUMENT_UPLOAD = 'DOCUMENT_UPLOAD', _('Document Upload')
    DOCUMENT_REVISION = 'DOCUMENT_REVISION', _('Document Revision')

class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices, db_index=True)
    entity = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['entity', 'entity_id']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_str} - {self.get_action_display()} on {self.entity} ({self.entity_id})"
