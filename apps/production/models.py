from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class ProcessStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    APPROVED = 'APPROVED', _('Approved')
    HOLD = 'HOLD', _('Hold')
    REJECTED = 'REJECTED', _('Rejected')

class MeasurementResult(models.TextChoices):
    PASS = 'PASS', _('Pass')
    FAIL = 'FAIL', _('Fail')
    HOLD = 'HOLD', _('Hold')

class PressingProcessType(models.TextChoices):
    BLANKING = 'BLANKING', _('Blanking')
    FORMING = 'FORMING', _('Forming')
    PEARLING = 'PEARLING', _('Pearling')
    RESTRICTING = 'RESTRICTING', _('Restricting')

class BendingRecord(models.Model):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='bending_record')
    tube_size = models.CharField(max_length=100, default='38.1 mm')
    thickness = models.CharField(max_length=100, default='2.0 mm')
    bending_spec = models.CharField(max_length=150, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bending_operations')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    # Stored measurements list: [{"parameter": "Bend Angle", "expected": "90 deg", "actual": "90.2", "tolerance": "±1 deg", "result": "PASS"}]
    measurements = models.JSONField(default=list, blank=True)
    critical_dimension_status = models.CharField(max_length=20, choices=MeasurementResult.choices, default=MeasurementResult.PASS)
    status = models.CharField(max_length=30, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bending: {self.product.product_id} [{self.status}]"

class PressingRecord(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='pressing_records')
    process_type = models.CharField(max_length=50, choices=PressingProcessType.choices, db_index=True)
    dim_report_number = models.CharField(max_length=100, blank=True, help_text="Required for Blanking")
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_produced = models.PositiveIntegerField(default=1)
    measurements = models.JSONField(default=list, blank=True)
    critical_dimension_result = models.CharField(max_length=20, choices=MeasurementResult.choices, default=MeasurementResult.PASS)
    status = models.CharField(max_length=30, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    remarks = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'process_type')
        ordering = ['process_type']

    def __str__(self):
        return f"Pressing ({self.process_type}): {self.product.product_id} [{self.status}]"

class WeldingRecord(models.Model):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='welding_records')
    stage_number = models.PositiveSmallIntegerField(default=1, help_text="Stage 1 to 5")
    stage_name = models.CharField(max_length=100, default='Stage 1')
    approved_sample_id = models.CharField(max_length=100, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    measurements = models.JSONField(default=list, blank=True)
    result = models.CharField(max_length=20, choices=MeasurementResult.choices, default=MeasurementResult.PASS)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='welding_signed_approvals')
    approval_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'stage_number')
        ordering = ['stage_number']

    def __str__(self):
        return f"Welding ({self.stage_name}): {self.product.product_id} [{self.status}]"

class PaintRecord(models.Model):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='paint_record')
    paint_specification = models.CharField(max_length=150, default='Powder Coating / RAL 7016')
    color_code = models.CharField(max_length=50, default='Anthracite Grey')
    thickness_microns = models.DecimalField(max_digits=6, decimal_places=2, default=85.00)
    
    # Dual Sign-off Requirements
    ceo_approved = models.BooleanField(default=False)
    ceo_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ceo_paint_approvals')
    ceo_approval_date = models.DateTimeField(null=True, blank=True)
    ceo_remarks = models.TextField(blank=True)

    pc_approved = models.BooleanField(default=False)
    pc_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pc_paint_approvals')
    pc_approval_date = models.DateTimeField(null=True, blank=True)
    pc_remarks = models.TextField(blank=True)

    status = models.CharField(max_length=30, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_fully_approved(self):
        return self.ceo_approved and self.pc_approved and self.status == ProcessStatus.APPROVED

    def __str__(self):
        return f"Paint: {self.product.product_id} [CEO:{self.ceo_approved}, PC:{self.pc_approved}]"

class PDIRecord(models.Model):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='pdi_record')
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    check_sheet_data = models.JSONField(default=list, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pdi_signoffs')
    approval_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PDI: {self.product.product_id} [{self.status}, Approved:{self.is_approved}]"
