from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

MODULE_CHOICES = [
    ('dashboard', _('Dashboard')),
    ('admins', _('Admins')),
    ('users', _('Users')),
    ('products', _('Products')),
    ('bending', _('Bending')),
    ('pressing', _('Pressing')),
    ('blanking', _('Blanking')),
    ('forming', _('Forming')),
    ('pearling', _('Pearling')),
    ('restricting', _('Restricting')),
    ('welding', _('Welding')),
    ('paint', _('Paint')),
    ('pdi', _('PDI (Pre-Dispatch Inspection)')),
    ('dispatch', _('Dispatch')),
    ('quality', _('Quality Management')),
    ('documents', _('Documents')),
    ('reports', _('Reports')),
    ('audit_logs', _('Audit Logs')),
    ('settings', _('Settings')),
]

class ModulePermission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='module_permissions')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_index=True)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'module')
        verbose_name = _('Module Permission')
        verbose_name_plural = _('Module Permissions')
        indexes = [
            models.Index(fields=['user', 'module']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.module} [V:{self.can_view}, C:{self.can_create}, E:{self.can_edit}, D:{self.can_delete}, A:{self.can_approve}, X:{self.can_export}]"

class PermissionTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    # Stored as a JSON dictionary mapping module_name -> list of granted actions ['view', 'create', 'edit', 'delete', 'approve', 'export']
    matrix = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AuthorityChangeLog(models.Model):
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_authority_changes')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='made_authority_changes')
    module = models.CharField(max_length=50)
    old_permissions = models.CharField(max_length=150)
    new_permissions = models.CharField(max_length=150)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.admin_user.username}: {self.module} changed by {self.changed_by.username if self.changed_by else 'System'}"
