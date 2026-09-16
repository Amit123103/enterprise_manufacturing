from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class UserStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    INACTIVE = 'INACTIVE', _('Inactive')
    SUSPENDED = 'SUSPENDED', _('Suspended')

class UserRole(models.TextChoices):
    SUPER_ADMIN = 'SUPER_ADMIN', _('Super Admin')
    ADMIN = 'ADMIN', _('Admin')
    USER = 'USER', _('User')
    # Specific specialized roles
    PRODUCTION_OPERATOR = 'PRODUCTION_OPERATOR', _('Production Operator')
    BENDING_OPERATOR = 'BENDING_OPERATOR', _('Bending Operator')
    PRESSING_OPERATOR = 'PRESSING_OPERATOR', _('Pressing Operator')
    BLANKING_OPERATOR = 'BLANKING_OPERATOR', _('Blanking Operator')
    FORMING_OPERATOR = 'FORMING_OPERATOR', _('Forming Operator')
    PEARLING_OPERATOR = 'PEARLING_OPERATOR', _('Pearling Operator')
    RESTRICTING_OPERATOR = 'RESTRICTING_OPERATOR', _('Restricting Operator')
    WELDING_OPERATOR = 'WELDING_OPERATOR', _('Welding Operator')
    PAINT_OPERATOR = 'PAINT_OPERATOR', _('Paint Operator')
    PDI_INSPECTOR = 'PDI_INSPECTOR', _('PDI Inspector')
    QUALITY_INSPECTOR = 'QUALITY_INSPECTOR', _('Quality Inspector')
    DISPATCH_OPERATOR = 'DISPATCH_OPERATOR', _('Dispatch Operator')
    VIEWER = 'VIEWER', _('Viewer')

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email is required'))
        if not username:
            raise ValueError(_('Username is required'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        extra_fields.setdefault('status', UserStatus.ACTIVE)
        return self.create_user(email, username, password, **extra_fields)

class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    full_name = models.CharField(_('full name'), max_length=150, blank=True)
    employee_id = models.CharField(_('employee ID'), max_length=50, unique=True, db_index=True)
    phone = models.CharField(_('phone number'), max_length=25, blank=True)
    role = models.CharField(_('role'), max_length=50, choices=UserRole.choices, default=UserRole.USER, db_index=True)
    status = models.CharField(_('status'), max_length=20, choices=UserStatus.choices, default=UserStatus.ACTIVE, db_index=True)
    department = models.CharField(_('department'), max_length=100, blank=True)
    designation = models.CharField(_('designation'), max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    # Hierarchy relations
    assigned_admin = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        help_text=_('Admin managing this user')
    )
    
    # Operational scope fields
    production_stage = models.CharField(
        _('production stage'),
        max_length=50,
        blank=True,
        help_text=_('Current assigned primary production stage, e.g. BENDING, PRESSING')
    )
    production_line = models.CharField(_('production line'), max_length=50, blank=True)
    shift = models.CharField(_('shift'), max_length=50, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'employee_id']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name or self.username} ({self.employee_id}) - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip() or self.username
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.role == UserRole.SUPER_ADMIN or self.is_superuser:
            raise ValidationError(_('Super Admin accounts cannot be deleted.'))
        super().delete(*args, **kwargs)

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN or self.is_superuser

    @property
    def is_admin_user(self):
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]

    @property
    def is_operator(self):
        return not self.is_admin_user

    @property
    def is_active_account(self):
        return self.is_active and self.status == UserStatus.ACTIVE

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_admins')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Admin Profile for {self.user.email}"

class AdminScope(models.Model):
    admin = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_scope')
    production_lines = models.JSONField(default=list, blank=True, help_text=_("List of allowed production lines"))
    departments = models.JSONField(default=list, blank=True, help_text=_("List of allowed departments"))
    stages = models.JSONField(default=list, blank=True, help_text=_("List of allowed production stages"))
    product_groups = models.JSONField(default=list, blank=True)
    locations = models.JSONField(default=list, blank=True)
    customers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Scope for {self.admin.email}"

    def can_access_stage(self, stage_name):
        if not self.stages:
            return True
        return stage_name.upper() in [s.upper() for s in self.stages]
