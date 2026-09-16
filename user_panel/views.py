import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden

from apps.accounts.models import User, UserRole
from apps.products.models import Product, StageChoices, ProductStatus
from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord, ProcessStatus, PressingProcessType
from apps.quality.models import Rejection, RejectionReason, RejectionStatus, Inspection, CriticalDimension
from apps.documents.models import Document, DocumentCategory
from apps.dispatch.models import DispatchRecord, DispatchStatus
from apps.dispatch.services import check_dispatch_eligibility
from apps.audit.services import log_audit, AuditAction
from apps.permissions.services import has_permission
from apps.permissions.decorators import permission_required_custom

# ==============================================================================
# OPERATOR DASHBOARD
# ==============================================================================
@login_required
def dashboard_view(request):
    user = request.user
    assigned_stage = user.production_stage or 'BENDING'

    # Filter products for operator
    my_products = Product.objects.filter(
        current_stage__iexact=assigned_stage
    ).exclude(status=ProductStatus.COMPLETED).order_by('-priority', '-created_at')

    # Status counts
    pending_tasks = my_products.filter(status=ProductStatus.PENDING).count()
    in_progress = my_products.filter(status=ProductStatus.IN_PROGRESS).count()
    hold_count = my_products.filter(status=ProductStatus.HOLD).count()

    context = {
        'assigned_stage': assigned_stage,
        'my_products': my_products[:8],
        'pending_tasks': pending_tasks,
        'in_progress': in_progress,
        'hold_count': hold_count,
    }
    return render(request, 'user_panel/dashboard.html', context)


# ==============================================================================
# MY PRODUCTS LIST
# ==============================================================================
@login_required
def my_products_view(request):
    user = request.user
    products = Product.objects.all().order_by('-created_at')
    if user.production_stage:
        products = products.filter(current_stage__iexact=user.production_stage)

    return render(request, 'user_panel/my_products.html', {'products': products})

@login_required
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    can_dispatch, dispatch_issues, stage_statuses = check_dispatch_eligibility(product)

    return render(request, 'user_panel/product_detail.html', {
        'product': product,
        'can_dispatch': can_dispatch,
        'dispatch_issues': dispatch_issues,
        'stage_statuses': stage_statuses,
        'is_admin': False,
    })


# ==============================================================================
# BENDING STAGE
# ==============================================================================
@login_required
@permission_required_custom('bending', 'view')
def bending_view(request):
    products = Product.objects.filter(current_stage=StageChoices.BENDING).order_by('-created_at')
    
    # SOP and Standard Documents for Bending
    bending_docs = Document.objects.filter(
        document_type__in=[DocumentCategory.DRAWINGS, DocumentCategory.PFD, DocumentCategory.PFMEA, DocumentCategory.CP, DocumentCategory.PACKING_STANDARD]
    )[:10]

    return render(request, 'user_panel/bending.html', {
        'products': products,
        'documents': bending_docs,
    })

@login_required
@permission_required_custom('bending', 'edit')
def bending_record_submit_view(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    
    if request.method == 'POST':
        tube_size = request.POST.get('tube_size', '38.1 mm')
        thickness = request.POST.get('thickness', '2.0 mm')
        bend_angle = request.POST.get('bend_angle', '90.0')
        critical_dimension_status = request.POST.get('critical_dimension_status', 'PASS')
        remarks = request.POST.get('remarks', '')

        record, created = BendingRecord.objects.get_or_create(product=product)
        record.tube_size = tube_size
        record.thickness = thickness
        record.critical_dimension_status = critical_dimension_status
        record.operator = request.user
        record.remarks = remarks
        record.measurements = [
            {"parameter": "Outer Diameter Tube Size", "expected": "38.1 mm", "actual": tube_size, "result": "PASS"},
            {"parameter": "Wall Thickness", "expected": "2.0 mm", "actual": thickness, "result": "PASS"},
            {"parameter": "Bend Angle", "expected": "90.0 deg", "actual": f"{bend_angle} deg", "result": critical_dimension_status},
        ]

        if critical_dimension_status == 'PASS':
            record.status = ProcessStatus.COMPLETED
            product.current_stage = StageChoices.PRESSING
            product.status = ProductStatus.IN_PROGRESS
            product.save(update_fields=['current_stage', 'status'])
            messages.success(request, f"Bending successfully completed for {product.product_id}. Moved to PRESSING.")
        else:
            record.status = ProcessStatus.HOLD
            product.status = ProductStatus.REJECTED
            product.save(update_fields=['status'])
            # Auto-create quality rejection as required by specification
            dim_reason, _ = RejectionReason.objects.get_or_create(
                name="Dimension Mismatch",
                defaults={'code': 'DEF-DIM', 'description': 'Critical dimension out of specified tolerance'}
            )
            Rejection.objects.create(
                product=product,
                stage="BENDING",
                reason=dim_reason,
                description=f"Critical dimension failure in Bending: Bend Angle actual {bend_angle} deg (Status: {critical_dimension_status}).",
                created_by=request.user,
                status=RejectionStatus.OPEN
            )
            messages.error(request, f"Critical Dimension FAILED on {product.product_id}. Non-conformance rejection created automatically!")

        record.save()
        log_audit(request, AuditAction.STAGE_COMPLETED, 'Bending', product.id, new_value=f"Bending evaluated: {critical_dimension_status}")
        return redirect('user_bending')

    record = getattr(product, 'bending_record', None)
    return render(request, 'user_panel/bending_form.html', {'product': product, 'record': record})


# ==============================================================================
# PRESSING STAGE (Blanking, Forming, Pearling, Restricting)
# ==============================================================================
@login_required
@permission_required_custom('pressing', 'view')
def pressing_view(request):
    process_type = request.GET.get('sub', 'ALL').upper()
    products = Product.objects.filter(current_stage=StageChoices.PRESSING).order_by('-created_at')

    return render(request, 'user_panel/pressing.html', {
        'products': products,
        'process_type': process_type,
        'subprocesses': ['BLANKING', 'FORMING', 'PEARLING', 'RESTRICTING'],
    })

@login_required
@permission_required_custom('pressing', 'edit')
def pressing_record_submit_view(request, product_id, proc_type):
    product = get_object_or_404(Product, product_id=product_id)
    proc_upper = proc_type.upper()

    if request.method == 'POST':
        dim_report = request.POST.get('dim_report_number', '')
        crit_result = request.POST.get('critical_dimension_result', 'PASS')
        remarks = request.POST.get('remarks', '')

        record, _ = PressingRecord.objects.get_or_create(product=product, process_type=proc_upper)
        record.dim_report_number = dim_report
        record.critical_dimension_result = crit_result
        record.operator = request.user
        record.status = ProcessStatus.COMPLETED if crit_result == 'PASS' else ProcessStatus.HOLD
        record.completed_at = timezone.now()
        record.remarks = remarks
        record.save()

        # Check if all 4 pressing processes are completed
        required = {'BLANKING', 'FORMING', 'PEARLING', 'RESTRICTING'}
        done = set(product.pressing_records.filter(status=ProcessStatus.COMPLETED).values_list('process_type', flat=True))
        
        if required.issubset(done):
            product.current_stage = StageChoices.WELDING
            product.save(update_fields=['current_stage'])
            messages.success(request, f"All 4 Pressing subprocesses completed! Product {product.product_id} advanced to WELDING.")
        else:
            remaining = required - done
            messages.info(request, f"Pressing ({proc_upper}) saved. Remaining operations for {product.product_id}: {', '.join(remaining)}")

        log_audit(request, AuditAction.STAGE_COMPLETED, f"Pressing-{proc_upper}", product.id, new_value=crit_result)
        return redirect('user_pressing')

    record = product.pressing_records.filter(process_type=proc_upper).first()
    return render(request, 'user_panel/pressing_form.html', {'product': product, 'proc_type': proc_upper, 'record': record})


# ==============================================================================
# WELDING STAGE (Configurable Stages 1 - 5)
# ==============================================================================
@login_required
@permission_required_custom('welding', 'view')
def welding_view(request):
    products = Product.objects.filter(current_stage=StageChoices.WELDING).order_by('-created_at')
    return render(request, 'user_panel/welding.html', {'products': products})

@login_required
@permission_required_custom('welding', 'edit')
def welding_stage_submit_view(request, product_id, stage_num):
    product = get_object_or_404(Product, product_id=product_id)
    stage_num = int(stage_num)

    if request.method == 'POST':
        sample_id = request.POST.get('approved_sample_id', '')
        result = request.POST.get('result', 'PASS')
        remarks = request.POST.get('remarks', '')

        record, _ = WeldingRecord.objects.get_or_create(product=product, stage_number=stage_num)
        record.stage_name = f"Stage {stage_num}"
        record.approved_sample_id = sample_id
        record.operator = request.user
        record.result = result
        record.status = ProcessStatus.COMPLETED if result == 'PASS' else ProcessStatus.HOLD
        record.remarks = remarks
        record.end_time = timezone.now()
        record.save()

        # If stage 5 completed, advance to PAINT
        if stage_num == 5 and result == 'PASS':
            product.current_stage = StageChoices.PAINT
            product.save(update_fields=['current_stage'])
            messages.success(request, f"Welding final Stage 5 completed! {product.product_id} advanced to PAINT.")
        else:
            messages.info(request, f"Welding Stage {stage_num} logged successfully for {product.product_id}.")

        log_audit(request, AuditAction.STAGE_COMPLETED, f"Welding-Stage-{stage_num}", product.id, new_value=result)
        return redirect('user_welding')

    record = product.welding_records.filter(stage_number=stage_num).first()
    return render(request, 'user_panel/welding_form.html', {'product': product, 'stage_num': stage_num, 'record': record})


# ==============================================================================
# PAINT STAGE (CEO & PC Approvals)
# ==============================================================================
@login_required
@permission_required_custom('paint', 'view')
def paint_view(request):
    products = Product.objects.filter(current_stage=StageChoices.PAINT).order_by('-created_at')
    return render(request, 'user_panel/paint.html', {'products': products})

@login_required
@permission_required_custom('paint', 'edit')
def paint_submit_view(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    
    if request.method == 'POST':
        spec = request.POST.get('paint_specification', 'Powder Coating / RAL 7016')
        color = request.POST.get('color_code', 'Anthracite Grey')
        thickness = request.POST.get('thickness_microns', '85.0')
        ceo_sign = 'ceo_approved' in request.POST
        pc_sign = 'pc_approved' in request.POST

        record, _ = PaintRecord.objects.get_or_create(product=product)
        record.paint_specification = spec
        record.color_code = color
        record.thickness_microns = float(thickness) if thickness else 85.0
        
        if ceo_sign:
            record.ceo_approved = True
            record.ceo_approved_by = request.user
            record.ceo_approval_date = timezone.now()
        if pc_sign:
            record.pc_approved = True
            record.pc_approved_by = request.user
            record.pc_approval_date = timezone.now()

        if record.ceo_approved and record.pc_approved:
            record.status = ProcessStatus.APPROVED
            record.completed_at = timezone.now()
            product.current_stage = StageChoices.PDI
            product.save(update_fields=['current_stage'])
            messages.success(request, f"Paint dual sign-offs (CEO & PC) completed! Advanced {product.product_id} to PDI.")
        else:
            record.status = ProcessStatus.IN_PROGRESS
            messages.info(request, f"Paint specs updated. Signatures: CEO: {'✓' if record.ceo_approved else 'Pending'}, PC: {'✓' if record.pc_approved else 'Pending'}")

        record.save()
        log_audit(request, AuditAction.APPROVAL, 'Paint', product.id, new_value=f"Paint sign-off: CEO={record.ceo_approved}, PC={record.pc_approved}")
        return redirect('user_paint')

    record = getattr(product, 'paint_record', None)
    return render(request, 'user_panel/paint_form.html', {'product': product, 'record': record})


# ==============================================================================
# PDI STAGE (Pre-Dispatch Inspection)
# ==============================================================================
@login_required
@permission_required_custom('pdi', 'view')
def pdi_view(request):
    products = Product.objects.filter(current_stage=StageChoices.PDI).order_by('-created_at')
    return render(request, 'user_panel/pdi.html', {'products': products})

@login_required
@permission_required_custom('pdi', 'edit')
def pdi_submit_view(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)

    if request.method == 'POST':
        is_pass = request.POST.get('pdi_result') == 'PASS'
        remarks = request.POST.get('remarks', '')

        pdi, _ = PDIRecord.objects.get_or_create(product=product)
        pdi.inspector = request.user
        pdi.remarks = remarks
        pdi.is_approved = is_pass
        pdi.approval_date = timezone.now()

        if is_pass:
            pdi.status = ProcessStatus.APPROVED
            pdi.approved_by = request.user
            product.current_stage = StageChoices.DISPATCH
            product.status = ProductStatus.APPROVED
            product.save(update_fields=['current_stage', 'status'])
            messages.success(request, f"PDI Inspection APPROVED for {product.product_id}! Product is now cleared for DISPATCH.")
        else:
            pdi.status = ProcessStatus.REJECTED
            product.status = ProductStatus.REJECTED
            product.save(update_fields=['status'])
            # Create rejection
            rej_reason, _ = RejectionReason.objects.get_or_create(name="PDI Inspection Defect", defaults={'code': 'DEF-PDI'})
            Rejection.objects.create(
                product=product,
                stage='PDI',
                reason=rej_reason,
                description=f"PDI Check sheet failure: {remarks}",
                created_by=request.user
            )
            messages.error(request, f"PDI Inspection FAILED for {product.product_id}. Rejection logged.")

        pdi.save()
        log_audit(request, AuditAction.INSPECTION, 'PDI', product.id, new_value=f"PDI: {'PASS' if is_pass else 'FAIL'}")
        return redirect('user_pdi')

    record = getattr(product, 'pdi_record', None)
    return render(request, 'user_panel/pdi_form.html', {'product': product, 'record': record})


# ==============================================================================
# DISPATCH (Strict Gatekeeper Clearance)
# ==============================================================================
@login_required
@permission_required_custom('dispatch', 'view')
def dispatch_view(request):
    products = Product.objects.filter(current_stage=StageChoices.DISPATCH).order_by('-created_at')
    
    # Check eligibility for each
    product_status_list = []
    for p in products:
        eligible, issues, _ = check_dispatch_eligibility(p)
        product_status_list.append({
            'product': p,
            'eligible': eligible,
            'issues': issues,
        })

    return render(request, 'user_panel/dispatch.html', {'product_status_list': product_status_list})

@login_required
@permission_required_custom('dispatch', 'edit')
def dispatch_submit_view(request, product_id):
    """
    CRITICAL DISPATCH GATEKEEPER:
    Must verify all previous stages (Bending, Pressing, Welding, Paint, PDI).
    If any check fails: DISPATCH IS STRICTLY BLOCKED!
    """
    product = get_object_or_404(Product, product_id=product_id)
    is_eligible, issues, stage_statuses = check_dispatch_eligibility(product)

    if not is_eligible:
        messages.error(request, f"DISPATCH BLOCKED for {product.product_id}! Reasons: {'; '.join(issues)}")
        return redirect('user_dispatch')

    if request.method == 'POST':
        vehicle = request.POST.get('vehicle_number', '').strip()
        transporter = request.POST.get('transporter', '').strip()
        invoice = request.POST.get('invoice_number', '').strip()
        remarks = request.POST.get('remarks', '')

        dispatch_rec, _ = DispatchRecord.objects.get_or_create(product=product)
        dispatch_rec.customer = product.customer
        dispatch_rec.vehicle_number = vehicle
        dispatch_rec.transporter = transporter
        dispatch_rec.invoice_number = invoice
        dispatch_rec.dispatched_by = request.user
        dispatch_rec.remarks = remarks
        dispatch_rec.status = DispatchStatus.DISPATCHED
        dispatch_rec.dispatch_date = timezone.now()
        dispatch_rec.save()

        # Mark product COMPLETED
        product.current_stage = StageChoices.COMPLETED
        product.status = ProductStatus.COMPLETED
        product.save(update_fields=['current_stage', 'status'])

        log_audit(
            request,
            AuditAction.DISPATCH,
            'Dispatch',
            product.id,
            new_value=f"Dispatched via {transporter} ({vehicle}), Invoice: {invoice}"
        )
        messages.success(request, f"Lot {product.product_id} successfully dispatched!")
        return redirect('user_dispatch')

    return render(request, 'user_panel/dispatch_form.html', {
        'product': product,
        'is_eligible': is_eligible,
        'issues': issues,
    })


# ==============================================================================
# SHOP FLOOR QR SCANNER
# ==============================================================================
@login_required
def scanner_view(request):
    if request.method == 'POST':
        prod_id = request.POST.get('product_id', '').strip()
        prod = Product.objects.filter(product_id__iexact=prod_id).first()
        if prod:
            return redirect('user_product_detail', product_id=prod.product_id)
        else:
            messages.error(request, f"Product tag '{prod_id}' not found in registry.")
    return render(request, 'user_panel/scanner.html')


# ==============================================================================
# OPERATOR DOCUMENTS VIEW
# ==============================================================================
@login_required
def documents_view(request):
    docs = Document.objects.filter(status='ACTIVE').order_by('-uploaded_date')
    return render(request, 'user_panel/documents.html', {'documents': docs})
