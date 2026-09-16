import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseForbidden

from apps.accounts.models import User, UserRole, UserStatus, AdminProfile, AdminScope
from apps.permissions.models import ModulePermission, PermissionTemplate, AuthorityChangeLog, MODULE_CHOICES
from apps.permissions.services import has_permission, apply_permission_template, update_user_permission, DEFAULT_TEMPLATES
from apps.permissions.decorators import permission_required_custom, super_admin_required, admin_required
from apps.products.models import Product, ProductPart, StageChoices, ProductStatus, PriorityChoices
from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord, ProcessStatus
from apps.quality.models import RejectionReason, CriticalDimension, Inspection, InspectionParameter, Rejection, RejectionStatus
from apps.documents.models import Document, DocumentCategory, DocumentStatus, ApprovedSample
from apps.dispatch.models import DispatchRecord, DispatchStatus
from apps.dispatch.services import check_dispatch_eligibility
from apps.audit.models import AuditLog, AuditAction
from apps.audit.services import log_audit
from apps.notifications.services import notify_user, notify_admins
from apps.reports.services import export_to_csv, export_to_excel, export_to_pdf
from admin_panel.forms import AdminCreationForm, UserCreationForm, ProductForm, DocumentUploadForm, RejectionForm

# ==============================================================================
# DASHBOARD
# ==============================================================================
@admin_required
def dashboard_view(request):
    user = request.user
    today = timezone.now().date()

    # Base Metrics
    total_admins = User.objects.filter(role=UserRole.ADMIN).count()
    active_admins = User.objects.filter(role=UserRole.ADMIN, status=UserStatus.ACTIVE).count()
    suspended_admins = User.objects.filter(role=UserRole.ADMIN, status=UserStatus.SUSPENDED).count()

    total_users = User.objects.exclude(role__in=[UserRole.SUPER_ADMIN, UserRole.ADMIN]).count()
    active_users = User.objects.exclude(role__in=[UserRole.SUPER_ADMIN, UserRole.ADMIN]).filter(status=UserStatus.ACTIVE).count()

    total_products = Product.objects.count()
    in_production = Product.objects.filter(status=ProductStatus.IN_PROGRESS).count()
    completed = Product.objects.filter(status=ProductStatus.COMPLETED).count()
    rejected = Product.objects.filter(status=ProductStatus.REJECTED).count()
    pending_approval = Product.objects.filter(status=ProductStatus.PENDING).count()

    ready_for_dispatch = Product.objects.filter(current_stage=StageChoices.DISPATCH).exclude(status=ProductStatus.REJECTED).count()
    dispatched_today = DispatchRecord.objects.filter(dispatch_date__date=today, status=DispatchStatus.DISPATCHED).count()

    # Stage breakdown for chart
    stages = [
        ('Bending', Product.objects.filter(current_stage=StageChoices.BENDING).count()),
        ('Pressing', Product.objects.filter(current_stage=StageChoices.PRESSING).count()),
        ('Welding', Product.objects.filter(current_stage=StageChoices.WELDING).count()),
        ('Paint', Product.objects.filter(current_stage=StageChoices.PAINT).count()),
        ('PDI', Product.objects.filter(current_stage=StageChoices.PDI).count()),
        ('Dispatch', Product.objects.filter(current_stage=StageChoices.DISPATCH).count()),
    ]
    stage_labels = [s[0] for s in stages]
    stage_counts = [s[1] for s in stages]

    # Quality Pass Rate
    total_inspections = Inspection.objects.count()
    passed_inspections = Inspection.objects.filter(result='PASS').count()
    pass_rate = round((passed_inspections / total_inspections * 100), 1) if total_inspections > 0 else 100.0

    # Recent Records
    recent_products = Product.objects.select_related('assigned_admin', 'assigned_user').order_by('-created_at')[:8]
    recent_rejections = Rejection.objects.select_related('product', 'reason', 'created_by').order_by('-date')[:6]
    recent_authority_changes = AuthorityChangeLog.objects.select_related('admin_user', 'changed_by').order_by('-timestamp')[:6]
    recent_audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:8]

    context = {
        'total_admins': total_admins,
        'active_admins': active_admins,
        'suspended_admins': suspended_admins,
        'total_users': total_users,
        'active_users': active_users,
        'total_products': total_products,
        'in_production': in_production,
        'completed': completed,
        'rejected': rejected,
        'pending_approval': pending_approval,
        'ready_for_dispatch': ready_for_dispatch,
        'dispatched_today': dispatched_today,
        'pass_rate': pass_rate,
        'stage_labels_json': json.dumps(stage_labels),
        'stage_counts_json': json.dumps(stage_counts),
        'recent_products': recent_products,
        'recent_rejections': recent_rejections,
        'recent_authority_changes': recent_authority_changes,
        'recent_audit_logs': recent_audit_logs,
        'is_super_admin': user.is_super_admin,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ==============================================================================
# ADMIN MANAGEMENT (Super Admin Only)
# ==============================================================================
@super_admin_required
def admins_list_view(request):
    admins = User.objects.filter(role=UserRole.ADMIN).select_related('admin_profile').order_by('-created_at')
    return render(request, 'admin_panel/admins_list.html', {'admins': admins})

@super_admin_required
def admin_create_view(request):
    """
    CRITICAL SECURITY:
    Only Super Admin can access this view.
    Creates Django User, assigns ADMIN role, creates AdminProfile, sets default permissions, logs audit.
    """
    if request.method == 'POST':
        form = AdminCreationForm(request.POST, request.FILES)
        if form.is_valid():
            admin_user = form.save(commit=False)
            admin_user.role = UserRole.ADMIN
            admin_user.is_staff = True
            admin_user.set_password(form.cleaned_data['password'])
            admin_user.save()

            # Create AdminProfile
            AdminProfile.objects.create(
                user=admin_user,
                department=form.cleaned_data.get('department', ''),
                designation=form.cleaned_data.get('designation', ''),
                notes=form.cleaned_data.get('notes', ''),
                created_by=request.user
            )
            # Create Default Scope
            AdminScope.objects.create(admin=admin_user)

            # Apply default Production Admin template initially
            apply_permission_template(admin_user, 'Production Admin', changed_by=request.user)

            # Log audit
            log_audit(
                request,
                AuditAction.ADMIN_CREATED,
                'Admin',
                admin_user.id,
                new_value=f"Created Admin: {admin_user.email} ({admin_user.employee_id})"
            )

            messages.success(request, f"Admin account for {admin_user.full_name or admin_user.username} created successfully!")
            return redirect('admin_authority', admin_id=admin_user.id)
    else:
        form = AdminCreationForm()

    return render(request, 'admin_panel/admin_create.html', {'form': form})

@super_admin_required
def admin_toggle_status_view(request, admin_id):
    """Suspend or Activate an Admin."""
    admin_user = get_object_or_404(User, id=admin_id, role=UserRole.ADMIN)
    if request.method == 'POST':
        action = request.POST.get('action')
        old_status = admin_user.status
        if action == 'suspend':
            admin_user.status = UserStatus.SUSPENDED
            admin_user.save()
            log_audit(request, AuditAction.ADMIN_SUSPENDED, 'Admin', admin_user.id, old_value=old_status, new_value='SUSPENDED')
            messages.warning(request, f"Admin {admin_user.email} has been SUSPENDED.")
        elif action == 'activate':
            admin_user.status = UserStatus.ACTIVE
            admin_user.save()
            log_audit(request, AuditAction.ADMIN_ACTIVATED, 'Admin', admin_user.id, old_value=old_status, new_value='ACTIVE')
            messages.success(request, f"Admin {admin_user.email} has been ACTIVATED.")
    return redirect('admins_list')

@super_admin_required
def admin_authority_view(request, admin_id):
    """
    Super Admin manages the fine-grained permission matrix for an Admin.
    Can apply predefined templates or customize each module permission.
    """
    admin_user = get_object_or_404(User, id=admin_id, role=UserRole.ADMIN)

    if request.method == 'POST':
        # Check if template application requested
        template_name = request.POST.get('apply_template')
        if template_name:
            if apply_permission_template(admin_user, template_name, changed_by=request.user):
                log_audit(
                    request,
                    AuditAction.PERMISSION_CHANGED,
                    'AdminAuthority',
                    admin_user.id,
                    new_value=f"Applied template {template_name}"
                )
                messages.success(request, f"Successfully applied template '{template_name}' to {admin_user.username}.")
            return redirect('admin_authority', admin_id=admin_user.id)

        # Custom matrix save
        for mod_code, _ in MODULE_CHOICES:
            if mod_code == 'admins':
                continue # Normal admin cannot have 'admins' module

            actions_dict = {
                'can_view': f"{mod_code}_view" in request.POST,
                'can_create': f"{mod_code}_create" in request.POST,
                'can_edit': f"{mod_code}_edit" in request.POST,
                'can_delete': f"{mod_code}_delete" in request.POST,
                'can_approve': f"{mod_code}_approve" in request.POST,
                'can_export': f"{mod_code}_export" in request.POST,
            }
            update_user_permission(admin_user, mod_code, actions_dict, changed_by=request.user)

        # Update Scope
        scope, _ = AdminScope.objects.get_or_create(admin=admin_user)
        scope.stages = request.POST.getlist('scope_stages')
        scope.departments = [d.strip() for d in request.POST.get('scope_departments', '').split(',') if d.strip()]
        scope.save()

        log_audit(
            request,
            AuditAction.PERMISSION_CHANGED,
            'AdminAuthority',
            admin_user.id,
            new_value="Updated customized permissions matrix and scope"
        )
        messages.success(request, f"Authority matrix for {admin_user.username} saved successfully!")
        return redirect('admin_authority', admin_id=admin_user.id)

    # Build matrix map
    existing_perms = {p.module: p for p in ModulePermission.objects.filter(user=admin_user)}
    matrix_rows = []
    for mod_code, mod_label in MODULE_CHOICES:
        if mod_code == 'admins':
            continue
        p = existing_perms.get(mod_code)
        matrix_rows.append({
            'code': mod_code,
            'label': mod_label,
            'can_view': p.can_view if p else False,
            'can_create': p.can_create if p else False,
            'can_edit': p.can_edit if p else False,
            'can_delete': p.can_delete if p else False,
            'can_approve': p.can_approve if p else False,
            'can_export': p.can_export if p else False,
        })

    scope, _ = AdminScope.objects.get_or_create(admin=admin_user)
    available_templates = list(DEFAULT_TEMPLATES.keys())
    change_history = AuthorityChangeLog.objects.filter(admin_user=admin_user).order_by('-timestamp')[:10]

    context = {
        'admin_user': admin_user,
        'matrix_rows': matrix_rows,
        'scope': scope,
        'available_templates': available_templates,
        'change_history': change_history,
    }
    return render(request, 'admin_panel/admin_authority.html', context)


# ==============================================================================
# USER MANAGEMENT
# ==============================================================================
@admin_required
@permission_required_custom('users', 'view')
def users_list_view(request):
    users = User.objects.exclude(role__in=[UserRole.SUPER_ADMIN, UserRole.ADMIN]).select_related('assigned_admin').order_by('-created_at')
    can_create_user = has_permission(request.user, 'users', 'create')
    return render(request, 'admin_panel/users_list.html', {'users': users, 'can_create_user': can_create_user})

@admin_required
@permission_required_custom('users', 'create')
def user_create_view(request):
    """
    Admins can create Users only if permitted.
    STRICT: Admin cannot assign SUPER_ADMIN or ADMIN roles.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST, request.FILES, admin_user=request.user)
        if form.is_valid():
            new_user = form.save(commit=False)
            # Enforce non-admin role
            if not request.user.is_super_admin and new_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return HttpResponseForbidden("You are not authorized to create administrative roles.")

            new_user.set_password(form.cleaned_data['password'])
            if not new_user.assigned_admin and request.user.role == UserRole.ADMIN:
                new_user.assigned_admin = request.user
            new_user.save()

            log_audit(
                request,
                AuditAction.USER_CREATED,
                'User',
                new_user.id,
                new_value=f"Created User: {new_user.email} ({new_user.get_role_display()})"
            )
            messages.success(request, f"User {new_user.full_name or new_user.username} created successfully!")
            return redirect('users_list')
    else:
        form = UserCreationForm(admin_user=request.user)

    return render(request, 'admin_panel/user_create.html', {'form': form})

@admin_required
@permission_required_custom('users', 'edit')
def user_edit_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_admin_user and not request.user.is_super_admin:
        return HttpResponseForbidden("You cannot edit administrative users.")

    if request.method == 'POST':
        form = UserCreationForm(request.POST, request.FILES, instance=target_user, admin_user=request.user)
        if form.is_valid():
            u = form.save(commit=False)
            if form.cleaned_data.get('password'):
                u.set_password(form.cleaned_data['password'])
            u.save()
            log_audit(request, AuditAction.USER_EDITED, 'User', u.id, new_value=f"Edited user details ({u.email})")
            messages.success(request, f"User {u.username} updated.")
            return redirect('users_list')
    else:
        form = UserCreationForm(instance=target_user, admin_user=request.user)

    return render(request, 'admin_panel/user_edit.html', {'form': form, 'target_user': target_user})


# ==============================================================================
# PRODUCT MANAGEMENT
# ==============================================================================
@admin_required
@permission_required_custom('products', 'view')
def products_list_view(request):
    products = Product.objects.select_related('assigned_admin', 'assigned_user').order_by('-created_at')
    can_create_product = has_permission(request.user, 'products', 'create')
    return render(request, 'admin_panel/products_list.html', {'products': products, 'can_create_product': can_create_product})

@admin_required
@permission_required_custom('products', 'create')
def product_create_view(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            log_audit(request, AuditAction.PRODUCT_CREATED, 'Product', product.id, new_value=f"Product {product.product_id}")
            messages.success(request, f"Product {product.product_id} registered with QR Code!")
            return redirect('product_detail', product_id=product.product_id)
    else:
        form = ProductForm()

    return render(request, 'admin_panel/product_create.html', {'form': form})

@admin_required
@permission_required_custom('products', 'view')
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    
    # Check dispatch eligibility
    can_dispatch, dispatch_issues, stage_statuses = check_dispatch_eligibility(product)
    
    # Child records
    bending = getattr(product, 'bending_record', None)
    pressing_records = product.pressing_records.all()
    welding_records = product.welding_records.all()
    paint = getattr(product, 'paint_record', None)
    pdi = getattr(product, 'pdi_record', None)
    dispatch = getattr(product, 'dispatch_record', None)
    inspections = product.inspections.prefetch_related('parameters').all()
    rejections = product.rejections.select_related('reason').all()
    documents = product.documents.all()
    samples = product.approved_samples.all()
    audit_trail = AuditLog.objects.filter(entity='Product', entity_id=str(product.id)).order_by('-timestamp')[:10]

    context = {
        'product': product,
        'can_dispatch': can_dispatch,
        'dispatch_issues': dispatch_issues,
        'stage_statuses': stage_statuses,
        'bending': bending,
        'pressing_records': pressing_records,
        'welding_records': welding_records,
        'paint': paint,
        'pdi': pdi,
        'dispatch': dispatch,
        'inspections': inspections,
        'rejections': rejections,
        'documents': documents,
        'samples': samples,
        'audit_trail': audit_trail,
        'is_admin': True,
    }
    return render(request, 'admin_panel/product_detail.html', context)


# ==============================================================================
# PRODUCTION OVERSIGHT
# ==============================================================================
@admin_required
def production_stage_view(request, stage_name):
    stage_upper = stage_name.upper()
    if not has_permission(request.user, stage_name.lower(), 'view'):
        return render(request, 'errors/403.html', {'module': stage_name, 'action': 'view'}, status=403)

    products = Product.objects.filter(current_stage=stage_upper).select_related('assigned_admin', 'assigned_user')
    return render(request, 'admin_panel/production_stage.html', {
        'stage_name': stage_upper,
        'products': products,
    })


# ==============================================================================
# QUALITY & REJECTIONS
# ==============================================================================
@admin_required
@permission_required_custom('quality', 'view')
def quality_management_view(request):
    rejections = Rejection.objects.select_related('product', 'reason', 'created_by').order_by('-date')
    inspections = Inspection.objects.select_related('product', 'inspector').order_by('-date')[:15]
    rejection_reasons = RejectionReason.objects.all()
    critical_dims = CriticalDimension.objects.select_related('product').all()[:15]

    return render(request, 'admin_panel/quality.html', {
        'rejections': rejections,
        'inspections': inspections,
        'rejection_reasons': rejection_reasons,
        'critical_dims': critical_dims,
    })

@admin_required
@permission_required_custom('quality', 'create')
def rejection_create_view(request):
    if request.method == 'POST':
        form = RejectionForm(request.POST)
        if form.is_valid():
            rej = form.save(commit=False)
            rej.created_by = request.user
            rej.save()
            # Update product status
            rej.product.status = ProductStatus.REJECTED
            rej.product.save(update_fields=['status'])
            log_audit(request, AuditAction.REJECTION, 'Product', rej.product.id, new_value=f"Rejection: {rej.reason.name}")
            messages.error(request, f"Quality Rejection registered for {rej.product.product_id}!")
            return redirect('quality_management')
    else:
        form = RejectionForm()

    return render(request, 'admin_panel/rejection_create.html', {'form': form})


# ==============================================================================
# DOCUMENTS & APPROVED SAMPLES
# ==============================================================================
@admin_required
@permission_required_custom('documents', 'view')
def documents_view(request):
    docs = Document.objects.select_related('product', 'uploaded_by').order_by('-uploaded_date')
    samples = ApprovedSample.objects.select_related('product', 'approved_by').order_by('-created_at')
    can_upload = has_permission(request.user, 'documents', 'create')

    return render(request, 'admin_panel/documents.html', {
        'documents': docs,
        'samples': samples,
        'can_upload': can_upload,
    })

@admin_required
@permission_required_custom('documents', 'create')
def document_upload_view(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
            log_audit(request, AuditAction.DOCUMENT_UPLOAD, 'Document', doc.id, new_value=doc.name)
            messages.success(request, f"Document '{doc.name}' uploaded successfully!")
            return redirect('documents_view')
    else:
        form = DocumentUploadForm()

    return render(request, 'admin_panel/document_upload.html', {'form': form})


# ==============================================================================
# REPORTS (CSV, Excel, PDF)
# ==============================================================================
@admin_required
@permission_required_custom('reports', 'view')
def reports_view(request):
    report_type = request.GET.get('type', 'production')
    export_format = request.GET.get('export', '')

    if report_type == 'quality':
        title = "Quality Inspection Report"
        headers = ["Inspection ID", "Product ID", "Stage", "Result", "Inspector", "Date", "Remarks"]
        inspections = Inspection.objects.select_related('product', 'inspector').order_by('-date')
        rows = [
            [
                i.inspection_id,
                i.product.product_id,
                i.stage,
                i.result,
                i.inspector.username if i.inspector else 'N/A',
                i.date.strftime('%Y-%m-%d %H:%M'),
                i.remarks
            ]
            for i in inspections
        ]
    elif report_type == 'rejections':
        title = "Manufacturing Rejection Report"
        headers = ["Product ID", "Stage", "Reason", "Status", "Date", "Corrective Action"]
        rejs = Rejection.objects.select_related('product', 'reason').order_by('-date')
        rows = [
            [
                r.product.product_id,
                r.stage,
                r.reason.name,
                r.get_status_display(),
                r.date.strftime('%Y-%m-%d'),
                r.corrective_action
            ]
            for r in rejs
        ]
    elif report_type == 'dispatch':
        title = "Dispatch & Clearance Report"
        headers = ["Product ID", "Customer", "Status", "Vehicle No", "Transporter", "Date"]
        dispatches = DispatchRecord.objects.select_related('product').order_by('-dispatch_date')
        rows = [
            [
                d.product.product_id,
                d.customer,
                d.get_status_display(),
                d.vehicle_number,
                d.transporter,
                d.dispatch_date.strftime('%Y-%m-%d')
            ]
            for d in dispatches
        ]
    else: # Production
        title = "Daily Production Pipeline Report"
        headers = ["Product ID", "Product Name", "Part Number", "Customer", "Stage", "Status", "Date"]
        prods = Product.objects.all().order_by('-created_at')
        rows = [
            [
                p.product_id,
                p.product_name,
                p.part_number,
                p.customer,
                p.get_current_stage_display(),
                p.get_status_display(),
                p.production_date.strftime('%Y-%m-%d')
            ]
            for p in prods
        ]

    # Handle Exports
    if export_format == 'csv':
        log_audit(request, 'REPORT_EXPORT', 'Report', new_value=f"Exported {report_type} CSV")
        return export_to_csv(f"{report_type}_report", headers, rows)
    elif export_format == 'excel':
        log_audit(request, 'REPORT_EXPORT', 'Report', new_value=f"Exported {report_type} Excel")
        return export_to_excel(f"{report_type}_report", title, headers, rows)
    elif export_format == 'pdf':
        log_audit(request, 'REPORT_EXPORT', 'Report', new_value=f"Exported {report_type} PDF")
        return export_to_pdf(f"{report_type}_report", title, f"Type: {report_type.upper()}", headers, rows)

    return render(request, 'admin_panel/reports.html', {
        'report_type': report_type,
        'title': title,
        'headers': headers,
        'rows': rows[:50],
        'total_count': len(rows),
    })


# ==============================================================================
# AUDIT LOGS
# ==============================================================================
@admin_required
@permission_required_custom('audit_logs', 'view')
def audit_logs_view(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    return render(request, 'admin_panel/audit_logs.html', {
        'logs': logs[:100],
        'action_choices': AuditAction.choices,
        'selected_action': action_filter,
    })


# ==============================================================================
# QR SCANNER
# ==============================================================================
@admin_required
def admin_scanner_view(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id', '').strip()
        product = Product.objects.filter(product_id__iexact=product_id).first()
        if product:
            return redirect('product_detail', product_id=product.product_id)
        else:
            messages.error(request, f"Product '{product_id}' not found in registry.")
    return render(request, 'admin_panel/scanner.html')


# ==============================================================================
# SETTINGS
# ==============================================================================
@super_admin_required
def settings_view(request):
    reasons = RejectionReason.objects.all()
    templates = PermissionTemplate.objects.all()
    return render(request, 'admin_panel/settings.html', {
        'reasons': reasons,
        'templates': templates,
    })
