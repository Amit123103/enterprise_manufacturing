from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class DocumentCategory(models.TextChoices):
    DRAWINGS = 'DRAWINGS', _('Drawings')
    PFD = 'PFD', _('PFD (Process Flow Diagram)')
    PFMEA = 'PFMEA', _('PFMEA (Failure Mode & Effects Analysis)')
    CP = 'CP', _('CP (Control Plan)')
    PS = 'PS', _('PS (Process Sheet)')
    PACKING_STANDARD = 'PACKING_STANDARD', _('Packing Standard')
    DIM_REPORT = 'DIM_REPORT', _('DIM Report')
    CRITICAL_DIMENSION = 'CRITICAL_DIMENSION', _('Critical Dimension Spec')
    INSPECTION_REPORT = 'INSPECTION_REPORT', _('Inspection Report')
    APPROVED_SAMPLE = 'APPROVED_SAMPLE', _('Approved Sample')

class DocumentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    DRAFT = 'DRAFT', _('Draft')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    ARCHIVED = 'ARCHIVED', _('Archived')

class SampleApprovalStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    ARCHIVED = 'ARCHIVED', _('Archived')

class Document(models.Model):
    name = models.CharField(max_length=200)
    document_type = models.CharField(max_length=50, choices=DocumentCategory.choices, db_index=True)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )
    part_number = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=20, default='1.0')
    revision = models.PositiveIntegerField(default=0)
    file = models.FileField(upload_to='documents/')
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_date']

    def __str__(self):
        return f"{self.name} (v{self.version}.r{self.revision}) - {self.get_document_type_display()}"

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=20)
    revision = models.PositiveIntegerField()
    file = models.FileField(upload_to='documents/versions/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    change_summary = models.TextField()

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document.name} - v{self.version}.r{self.revision}"

class ApprovedSample(models.Model):
    sample_id = models.CharField(max_length=50, unique=True, db_index=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='approved_samples')
    part_number = models.CharField(max_length=100)
    sample_name = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default='1.0')
    revision = models.PositiveIntegerField(default=0)
    drawing_file = models.FileField(upload_to='samples/drawings/', blank=True, null=True)
    sample_image = models.ImageField(upload_to='samples/images/', blank=True, null=True)
    critical_dimensions_summary = models.TextField(blank=True)
    approval_status = models.CharField(
        max_length=30,
        choices=SampleApprovalStatus.choices,
        default=SampleApprovalStatus.DRAFT,
        db_index=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_sample_records'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sample_id} - {self.sample_name} ({self.approval_status})"

    def save(self, *args, **kwargs):
        if not self.sample_id:
            year = timezone.now().year
            last = ApprovedSample.objects.filter(sample_id__startswith=f"SAMPLE-{year}-").order_by('-id').first()
            seq = 1
            if last:
                try:
                    seq = int(last.sample_id.split('-')[-1]) + 1
                except ValueError:
                    seq = 1
            self.sample_id = f"SAMPLE-{year}-{seq:04d}"
        super().save(*args, **kwargs)
