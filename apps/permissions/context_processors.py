from apps.permissions.services import get_user_modules, has_permission

def permissions_processor(request):
    """Expose permission helpers and module access to templates."""
    if not request.user.is_authenticated:
        return {
            'user_modules': {},
            'user_is_super_admin': False,
            'user_is_admin': False,
            'user_is_operator': False,
            'can_access': lambda module, action='view': False,
        }

    modules = get_user_modules(request.user)

    def can_access_fn(module, action='view'):
        return has_permission(request.user, module, action)

    return {
        'user_modules': modules,
        'user_is_super_admin': request.user.is_super_admin,
        'user_is_admin': request.user.is_admin_user,
        'user_is_operator': request.user.is_operator,
        'can_access': can_access_fn,
    }
