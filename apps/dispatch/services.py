from apps.production.models import BendingRecord, PressingRecord, WeldingRecord, PaintRecord, PDIRecord, ProcessStatus
from apps.quality.models import Rejection, RejectionStatus

def check_dispatch_eligibility(product):
    """
    Validates that a product has successfully passed all manufacturing stages:
    1. Bending completed and passed
    2. Pressing (Blanking, Forming, Pearling, Restricting) completed
    3. Welding completed and approved
    4. Paint dual approval (CEO and PC) completed
    5. PDI pre-dispatch inspection completed and approved
    6. No unresolved rejections

    Returns:
        tuple: (is_eligible: bool, issues: list of str, stage_statuses: dict)
    """
    issues = []
    stage_statuses = {
        'bending': 'PENDING',
        'pressing': 'PENDING',
        'welding': 'PENDING',
        'paint': 'PENDING',
        'pdi': 'PENDING',
        'rejections': 'CLEAR',
    }

    # 1. Bending Verification
    try:
        bending = product.bending_record
        if bending.status in [ProcessStatus.COMPLETED, ProcessStatus.APPROVED] and bending.critical_dimension_status == 'PASS':
            stage_statuses['bending'] = 'PASSED'
        else:
            issues.append(f"Bending stage incomplete or not passed (Current: {bending.get_status_display()}).")
            stage_statuses['bending'] = 'FAILED'
    except BendingRecord.DoesNotExist:
        issues.append("Bending stage has not been executed yet.")
        stage_statuses['bending'] = 'MISSING'

    # 2. Pressing Verification
    pressing_records = product.pressing_records.all()
    required_pressing = {'BLANKING', 'FORMING', 'PEARLING', 'RESTRICTING'}
    completed_pressing = set(
        pressing_records.filter(status__in=[ProcessStatus.COMPLETED, ProcessStatus.APPROVED]).values_list('process_type', flat=True)
    )
    missing_pressing = required_pressing - completed_pressing
    if missing_pressing:
        issues.append(f"Pressing operations incomplete: missing {', '.join(missing_pressing)}.")
        stage_statuses['pressing'] = 'INCOMPLETE'
    else:
        stage_statuses['pressing'] = 'PASSED'

    # 3. Welding Verification
    welding_records = product.welding_records.all()
    if not welding_records.exists():
        issues.append("Welding stages have not been performed.")
        stage_statuses['welding'] = 'MISSING'
    else:
        incomplete_welds = welding_records.exclude(status__in=[ProcessStatus.COMPLETED, ProcessStatus.APPROVED])
        if incomplete_welds.exists():
            issues.append(f"Welding has {incomplete_welds.count()} stage(s) pending completion or approval.")
            stage_statuses['welding'] = 'INCOMPLETE'
        else:
            stage_statuses['welding'] = 'PASSED'

    # 4. Paint Verification (Dual CEO + PC approval required)
    try:
        paint = product.paint_record
        if paint.ceo_approved and paint.pc_approved and paint.status in [ProcessStatus.COMPLETED, ProcessStatus.APPROVED]:
            stage_statuses['paint'] = 'PASSED'
        else:
            reasons = []
            if not paint.ceo_approved: reasons.append("CEO sign-off pending")
            if not paint.pc_approved: reasons.append("PC sign-off pending")
            if paint.status not in [ProcessStatus.COMPLETED, ProcessStatus.APPROVED]: reasons.append(f"Status: {paint.status}")
            issues.append(f"Paint approval incomplete ({', '.join(reasons)}).")
            stage_statuses['paint'] = 'INCOMPLETE'
    except PaintRecord.DoesNotExist:
        issues.append("Paint process record is missing.")
        stage_statuses['paint'] = 'MISSING'

    # 5. PDI Verification
    try:
        pdi = product.pdi_record
        if pdi.is_approved and pdi.status in [ProcessStatus.COMPLETED, ProcessStatus.APPROVED]:
            stage_statuses['pdi'] = 'PASSED'
        else:
            issues.append("Pre-Dispatch Inspection (PDI) has not been approved.")
            stage_statuses['pdi'] = 'INCOMPLETE'
    except PDIRecord.DoesNotExist:
        issues.append("Pre-Dispatch Inspection (PDI) record is missing.")
        stage_statuses['pdi'] = 'MISSING'

    # 6. Check for unresolved rejections
    open_rejections = product.rejections.filter(status__in=[RejectionStatus.OPEN, RejectionStatus.UNDER_REVIEW])
    if open_rejections.exists():
        issues.append(f"Product has {open_rejections.count()} unresolved quality rejection(s).")
        stage_statuses['rejections'] = 'BLOCKED'

    is_eligible = len(issues) == 0
    return is_eligible, issues, stage_statuses
