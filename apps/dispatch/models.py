from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class DispatchStatus(models.TextChoices):
    READY = 'READY', _('Ready for Dispatch')
    DISPATCHED = 'DISPATCHED', _('Dispatched')
    CANCELLED = 'CANCELLED', _('Cancelled')

class DispatchRecord(models.Model):
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='dispatch_record')
    customer = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    packing_status = models.CharField(max_length=150, default='Approved Standard Crate Packaging')
    dispatch_date = models.DateTimeField(default=timezone.now)
    vehicle_number = models.CharField(max_length=50)
    transporter = models.CharField(max_length=100)
    invoice_number = models.CharField(max_length=100)
    reference_number = models.CharField(max_length=100, blank=True)
    dispatched_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='dispatches_handled')
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=DispatchStatus.choices, default=DispatchStatus.READY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dispatch: {self.product.product_id} -> {self.customer} [{self.status}]"
