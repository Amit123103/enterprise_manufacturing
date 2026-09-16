from django import forms
from apps.accounts.models import User, UserRole, UserStatus, AdminProfile, AdminScope
from apps.products.models import Product, ProductPart, PriorityChoices, StageChoices, ProductStatus
from apps.quality.models import RejectionReason, CriticalDimension, Inspection, InspectionParameter, Rejection
from apps.documents.models import Document, DocumentCategory, DocumentStatus, ApprovedSample
from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord
from apps.dispatch.models import DispatchRecord

class AdminCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••••••'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••••••'}))
    notes = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)

    class Meta:
        model = User
        fields = [
            'full_name', 'employee_id', 'email', 'phone', 'username',
            'department', 'designation', 'profile_image', 'status'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned_data

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••••••'}))

    class Meta:
        model = User
        fields = [
            'full_name', 'employee_id', 'email', 'phone', 'username',
            'department', 'designation', 'role', 'assigned_admin',
            'production_stage', 'production_line', 'shift', 'status',
            'profile_image', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'assigned_admin': forms.Select(attrs={'class': 'form-select'}),
            'production_stage': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'None / Multi-stage'),
                ('BENDING', 'Bending'),
                ('PRESSING', 'Pressing (All 4 Processes)'),
                ('BLANKING', 'Pressing - Blanking'),
                ('FORMING', 'Pressing - Forming'),
                ('PEARLING', 'Pressing - Pearling'),
                ('RESTRICTING', 'Pressing - Restricting'),
                ('WELDING', 'Welding'),
                ('PAINT', 'Paint'),
                ('PDI', 'PDI Inspection'),
                ('DISPATCH', 'Dispatch'),
            ]),
            'production_line': forms.TextInput(attrs={'class': 'form-control'}),
            'shift': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        admin_user = kwargs.pop('admin_user', None)
        super().__init__(*args, **kwargs)
        # Limit assigned_admin choices to Admins
        self.fields['assigned_admin'].queryset = User.objects.filter(role__in=[UserRole.SUPER_ADMIN, UserRole.ADMIN])
        # If normal admin is creating, non-super admin can only assign specific roles (cannot assign SUPER_ADMIN or ADMIN)
        if admin_user and not admin_user.is_super_admin:
            allowed_roles = [
                choice for choice in UserRole.choices 
                if choice[0] not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            ]
            self.fields['role'].choices = allowed_roles
            self.fields['assigned_admin'].initial = admin_user

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_name', 'part_number', 'customer', 'model',
            'batch_number', 'production_date', 'assigned_admin',
            'assigned_user', 'current_stage', 'status', 'priority'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control'}),
            'customer': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'production_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assigned_admin': forms.Select(attrs={'class': 'form-select'}),
            'assigned_user': forms.Select(attrs={'class': 'form-select'}),
            'current_stage': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'document_type', 'product', 'part_number', 'version', 'revision', 'file', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'revision': forms.NumberInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class RejectionForm(forms.ModelForm):
    class Meta:
        model = Rejection
        fields = ['product', 'stage', 'reason', 'description', 'status', 'corrective_action']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('BENDING', 'Bending'),
                ('PRESSING', 'Pressing'),
                ('WELDING', 'Welding'),
                ('PAINT', 'Paint'),
                ('PDI', 'PDI'),
                ('DISPATCH', 'Dispatch'),
            ]),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'corrective_action': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
