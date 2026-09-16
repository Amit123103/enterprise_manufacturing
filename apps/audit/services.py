from apps.audit.models import AuditLog, AuditAction

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_audit(user_or_request, action, entity, entity_id='', old_value='', new_value='', ip_address=None):
    """Utility function to reliably record an audit log event."""
    user = None
    ip = ip_address

    if hasattr(user_or_request, 'user'):
        request = user_or_request
        user = request.user if request.user.is_authenticated else None
        if not ip:
            ip = get_client_ip(request)
    elif user_or_request and hasattr(user_or_request, 'is_authenticated') and user_or_request.is_authenticated:
        user = user_or_request

    return AuditLog.objects.create(
        user=user,
        action=action,
        entity=str(entity),
        entity_id=str(entity_id),
        old_value=str(old_value) if old_value is not None else '',
        new_value=str(new_value) if new_value is not None else '',
        ip_address=ip
    )
