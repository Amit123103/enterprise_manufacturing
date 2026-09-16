import os
from io import BytesIO
from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import qrcode

class StageChoices(models.TextChoices):
    BENDING = 'BENDING', _('Bending')
    PRESSING = 'PRESSING', _('Pressing')
    WELDING = 'WELDING', _('Welding')
    PAINT = 'PAINT', _('Paint')
    PDI = 'PDI', _('PDI (Pre-Dispatch Inspection)')
    DISPATCH = 'DISPATCH', _('Dispatch')
    COMPLETED = 'COMPLETED', _('Completed')

class ProductStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    HOLD = 'HOLD', _('Hold')

class PriorityChoices(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    URGENT = 'URGENT', _('Urgent')

class Product(models.Model):
    product_id = models.CharField(max_length=50, unique=True, db_index=True)
    product_name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, db_index=True)
    customer = models.CharField(max_length=150)
    model = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    production_date = models.DateField(default=timezone.now)
    
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_products'
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_products'
    )
    
    current_stage = models.CharField(
        max_length=50,
        choices=StageChoices.choices,
        default=StageChoices.BENDING,
        db_index=True
    )
    status = models.CharField(
        max_length=50,
        choices=ProductStatus.choices,
        default=ProductStatus.PENDING,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=PriorityChoices.choices,
        default=PriorityChoices.MEDIUM
    )
    
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_data = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['current_stage', 'status']),
            models.Index(fields=['customer', 'batch_number']),
        ]

    def __str__(self):
        return f"{self.product_id} - {self.product_name} ({self.get_current_stage_display()})"

    def save(self, *args, **kwargs):
        if not self.product_id:
            year = timezone.now().year
            last_prod = Product.objects.filter(product_id__startswith=f"PROD-{year}-").order_by('-id').first()
            if last_prod:
                try:
                    last_num = int(last_prod.product_id.split('-')[-1])
                    seq = last_num + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
            self.product_id = f"PROD-{year}-{seq:05d}"

        # Generate QR code if not exists
        if not self.qr_code_image:
            self.generate_qr_code(save_instance=False)

        super().save(*args, **kwargs)

    def generate_qr_code(self, save_instance=True):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        # Embedded payload
        data = f"MFG-ID:{self.product_id}|PART:{self.part_number}|CUST:{self.customer}"
        self.qr_data = data
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        file_name = f"{self.product_id}_qr.png"
        self.qr_code_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
        if save_instance:
            self.save(update_fields=['qr_code_image', 'qr_data'])

    @property
    def stage_sequence(self):
        return ['BENDING', 'PRESSING', 'WELDING', 'PAINT', 'PDI', 'DISPATCH']

    @property
    def stage_progress_percent(self):
        order = self.stage_sequence
        if self.current_stage == StageChoices.COMPLETED:
            return 100
        try:
            idx = order.index(self.current_stage)
            return int((idx / len(order)) * 100)
        except ValueError:
            return 0

class ProductPart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='parts')
    part_name = models.CharField(max_length=150)
    part_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    specification = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.part_name} ({self.part_number}) x {self.quantity}"
