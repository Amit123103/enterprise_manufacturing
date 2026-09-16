from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class InspectionResult(models.TextChoices):
    PASS = 'PASS', _('Pass')
    FAIL = 'FAIL', _('Fail')
    HOLD = 'HOLD', _('Hold')

class RejectionStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    SCRAPPED = 'SCRAPPED', _('Scrapped')
    REWORKED = 'REWORKED', _('Reworked')
    RESOLVED = 'RESOLVED', _('Resolved')

class RejectionReason(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class CriticalDimension(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='critical_dimensions')
    stage = models.CharField(max_length=50, db_index=True)
    parameter = models.CharField(max_length=150)
    nominal_value = models.DecimalField(max_digits=10, decimal_places=3)
    tolerance_min = models.DecimalField(max_digits=10, decimal_places=3)
    tolerance_max = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20, default='mm')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.product.product_id} [{self.stage}] - {self.parameter}: {self.nominal_value} {self.unit} (+{self.tolerance_max}/-{self.tolerance_min})"

class Inspection(models.Model):
    inspection_id = models.CharField(max_length=50, unique=True, db_index=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='inspections')
    stage = models.CharField(max_length=50, db_index=True)
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inspections_conducted'
    )
    date = models.DateTimeField(default=timezone.now)
    result = models.CharField(max_length=20, choices=InspectionResult.choices, default=InspectionResult.PASS)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.inspection_id} - {self.product.product_id} ({self.stage}): {self.result}"

    def save(self, *args, **kwargs):
        if not self.inspection_id:
            year = timezone.now().year
            last = Inspection.objects.filter(inspection_id__startswith=f"INSP-{year}-").order_by('-id').first()
            seq = 1
            if last:
                try:
                    seq = int(last.inspection_id.split('-')[-1]) + 1
                except ValueError:
                    seq = 1
            self.inspection_id = f"INSP-{year}-{seq:05d}"
        super().save(*args, **kwargs)

class InspectionParameter(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='parameters')
    parameter = models.CharField(max_length=150)
    expected_value = models.CharField(max_length=100)
    actual_value = models.CharField(max_length=100)
    tolerance = models.CharField(max_length=100, blank=True)
    result = models.CharField(max_length=20, choices=InspectionResult.choices, default=InspectionResult.PASS)
    is_critical = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.parameter}: exp {self.expected_value}, act {self.actual_value} -> {self.result}"

class Rejection(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='rejections')
    stage = models.CharField(max_length=50, db_index=True)
    reason = models.ForeignKey(RejectionReason, on_delete=models.PROTECT, related_name='rejections')
    description = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logged_rejections'
    )
    date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=RejectionStatus.choices, default=RejectionStatus.OPEN)
    corrective_action = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Rejection: {self.product.product_id} [{self.stage}] - {self.reason.name} ({self.status})"
