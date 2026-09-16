from functools import wraps
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden, JsonResponse
from apps.permissions.services import has_permission
from apps.accounts.models import UserRole

def permission_required_custom(module, action='view'):
    """
    Decorator for views to enforce module-level action permissions.
    Returns 403 Forbidden with custom error template if denied.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if not has_permission(request.user, module, action):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Permission Denied',
                        'detail': f"You do not have permission to '{action}' in module '{module}'."
                    }, status=403)

                return render(request, 'errors/403.html', {
                    'module': module,
                    'action': action,
                    'message': f"You do not have '{action}' authority for the '{module}' module. Please contact your system administrator."
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def super_admin_required(view_func):
    """Ensure user is Super Admin only."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not request.user.is_super_admin:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Super Admin access required'}, status=403)
            return render(request, 'errors/403.html', {
                'message': 'Super Administrator privilege is strictly required for this administrative operation.'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Ensure user is Super Admin or Admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not request.user.is_admin_user:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return JsonResponse({'error': 'Admin access required'}, status=403)
            return render(request, 'errors/403.html', {
                'message': 'Administrative privileges are required to access this resource.'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_required(view_func):
    """Ensure user is logged in as an operator or admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
