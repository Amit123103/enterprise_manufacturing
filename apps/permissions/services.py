from apps.permissions.models import ModulePermission, PermissionTemplate, AuthorityChangeLog, MODULE_CHOICES
from apps.accounts.models import UserRole

DEFAULT_TEMPLATES = {
    'Production Admin': {
        'dashboard': ['view'],
        'products': ['view', 'create', 'edit'],
        'bending': ['view', 'create', 'edit'],
        'pressing': ['view', 'create', 'edit'],
        'blanking': ['view', 'create', 'edit'],
        'forming': ['view', 'create', 'edit'],
        'pearling': ['view', 'create', 'edit'],
        'restricting': ['view', 'create', 'edit'],
        'users': ['view', 'create', 'edit'],
        'reports': ['view', 'export'],
        'documents': ['view'],
    },
    'Quality Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'quality': ['view', 'create', 'edit', 'approve', 'export'],
        'pdi': ['view', 'create', 'edit', 'approve', 'export'],
        'documents': ['view', 'create', 'edit'],
        'reports': ['view', 'export'],
        'users': ['view'],
    },
    'Welding Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'welding': ['view', 'create', 'edit', 'approve', 'export'],
        'quality': ['view'],
        'documents': ['view'],
        'reports': ['view', 'export'],
        'users': ['view', 'create', 'edit'],
    },
    'Paint Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'paint': ['view', 'create', 'edit', 'approve', 'export'],
        'quality': ['view'],
        'documents': ['view'],
        'reports': ['view', 'export'],
        'users': ['view', 'create', 'edit'],
    },
    'PDI Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'pdi': ['view', 'create', 'edit', 'approve', 'export'],
        'quality': ['view', 'create', 'edit', 'approve'],
        'documents': ['view'],
        'reports': ['view', 'export'],
        'users': ['view'],
    },
    'Dispatch Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'dispatch': ['view', 'create', 'edit', 'approve', 'export'],
        'reports': ['view', 'export'],
        'users': ['view'],
    },
    'Document Admin': {
        'dashboard': ['view'],
        'products': ['view'],
        'documents': ['view', 'create', 'edit', 'delete', 'approve', 'export'],
        'reports': ['view', 'export'],
    },
    'Operations Admin': {
        'dashboard': ['view'],
        'products': ['view', 'create', 'edit', 'approve', 'export'],
        'bending': ['view', 'create', 'edit', 'approve'],
        'pressing': ['view', 'create', 'edit', 'approve'],
        'blanking': ['view', 'create', 'edit', 'approve'],
        'forming': ['view', 'create', 'edit', 'approve'],
        'pearling': ['view', 'create', 'edit', 'approve'],
        'restricting': ['view', 'create', 'edit', 'approve'],
        'welding': ['view', 'create', 'edit', 'approve'],
        'paint': ['view', 'create', 'edit', 'approve'],
        'pdi': ['view', 'create', 'edit', 'approve'],
        'dispatch': ['view', 'create', 'edit', 'approve'],
        'quality': ['view', 'create', 'edit', 'approve'],
        'documents': ['view', 'create', 'edit', 'approve'],
        'reports': ['view', 'export'],
        'users': ['view', 'create', 'edit'],
    },
    'Full Admin': {
        mod[0]: ['view', 'create', 'edit', 'delete', 'approve', 'export']
        for mod in MODULE_CHOICES if mod[0] != 'admins'
    }
}

def has_permission(user, module, action='view'):
    """
    Check if a user has permission for a specific module and action.
    Super Admins have unrestricted access to everything.
    """
    if not user or not user.is_authenticated:
        return False

    if user.status != 'ACTIVE':
        return False

    # Super admin bypasses all module checks
    if user.is_super_admin:
        return True

    # Critical Security Rule: Only Super Admin can manage Admins
    if module == 'admins':
        return False

    action_field = f"can_{action.lower()}"
    try:
        perm = ModulePermission.objects.get(user=user, module=module)
        return getattr(perm, action_field, False)
    except ModulePermission.DoesNotExist:
        # Fallback for operators by assigned stage
        if user.is_operator:
            if action == 'view' and module in ['dashboard', 'products', 'notifications']:
                return True
            if user.production_stage and module.lower() == user.production_stage.lower():
                return True
            # Subprocesses of pressing
            if user.production_stage == 'PRESSING' and module.lower() in ['pressing', 'blanking', 'forming', 'pearling', 'restricting']:
                return True
        return False

def get_user_modules(user):
    """Return dictionary of module -> list of granted actions for the user."""
    if not user or not user.is_authenticated:
        return {}

    all_modules = [m[0] for m in MODULE_CHOICES]
    if user.is_super_admin:
        return {m: ['view', 'create', 'edit', 'delete', 'approve', 'export'] for m in all_modules}

    perms = ModulePermission.objects.filter(user=user)
    result = {}
    for p in perms:
        actions = []
        if p.can_view: actions.append('view')
        if p.can_create: actions.append('create')
        if p.can_edit: actions.append('edit')
        if p.can_delete: actions.append('delete')
        if p.can_approve: actions.append('approve')
        if p.can_export: actions.append('export')
        if actions:
            result[p.module] = actions

    # Ensure operators have their assigned stage visible
    if user.is_operator:
        if 'dashboard' not in result: result['dashboard'] = ['view']
        if 'products' not in result: result['products'] = ['view']
        stage = (user.production_stage or '').lower()
        if stage and stage not in result:
            result[stage] = ['view', 'create', 'edit']
        if stage == 'pressing':
            for sub in ['blanking', 'forming', 'pearling', 'restricting']:
                if sub not in result:
                    result[sub] = ['view', 'create', 'edit']

    return result

def apply_permission_template(user, template_name, changed_by=None):
    """Apply a predefined permission template to an Admin or User."""
    matrix = DEFAULT_TEMPLATES.get(template_name)
    if not matrix:
        try:
            tpl = PermissionTemplate.objects.get(name=template_name)
            matrix = tpl.matrix
        except PermissionTemplate.DoesNotExist:
            return False

    # Clear existing permissions
    ModulePermission.objects.filter(user=user).delete()

    for module, actions in matrix.items():
        # Normal admin cannot have 'admins' module permission
        if module == 'admins' and not user.is_super_admin:
            continue
            
        ModulePermission.objects.create(
            user=user,
            module=module,
            can_view='view' in actions,
            can_create='create' in actions,
            can_edit='edit' in actions,
            can_delete='delete' in actions,
            can_approve='approve' in actions,
            can_export='export' in actions,
        )

    if changed_by:
        AuthorityChangeLog.objects.create(
            admin_user=user,
            changed_by=changed_by,
            module="ALL (Template Applied)",
            old_permissions="Previous Profile",
            new_permissions=f"Applied Template: {template_name}"
        )
    return True

def update_user_permission(user, module, actions_dict, changed_by=None):
    """Update single module permission for a user and log the change."""
    if module == 'admins' and not (changed_by and changed_by.is_super_admin):
        return None

    perm, created = ModulePermission.objects.get_or_create(user=user, module=module)
    old_repr = f"V:{perm.can_view},C:{perm.can_create},E:{perm.can_edit},D:{perm.can_delete},A:{perm.can_approve},X:{perm.can_export}"

    perm.can_view = bool(actions_dict.get('can_view'))
    perm.can_create = bool(actions_dict.get('can_create'))
    perm.can_edit = bool(actions_dict.get('can_edit'))
    perm.can_delete = bool(actions_dict.get('can_delete'))
    perm.can_approve = bool(actions_dict.get('can_approve'))
    perm.can_export = bool(actions_dict.get('can_export'))
    perm.save()

    new_repr = f"V:{perm.can_view},C:{perm.can_create},E:{perm.can_edit},D:{perm.can_delete},A:{perm.can_approve},X:{perm.can_export}"

    if old_repr != new_repr and changed_by:
        AuthorityChangeLog.objects.create(
            admin_user=user,
            changed_by=changed_by,
            module=module,
            old_permissions=old_repr,
            new_permissions=new_repr
        )
    return perm
