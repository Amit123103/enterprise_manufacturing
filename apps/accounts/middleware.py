from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpResponseForbidden
from apps.accounts.models import UserStatus, UserRole

class UserStatusCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check account status
            if request.user.status == UserStatus.SUSPENDED:
                logout(request)
                messages.error(request, "Your account has been suspended. Please contact the Super Administrator.")
                return redirect('login')
            elif request.user.status == UserStatus.INACTIVE:
                logout(request)
                messages.error(request, "Your account is currently inactive. Please contact your administrator.")
                return redirect('login')

            # Strict Panel Protection
            path = request.path
            # Admin Panel requires Super Admin or Admin role
            if path.startswith('/admin-panel/'):
                if not (request.user.is_superuser or request.user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]):
                    return render(request, 'errors/403.html', {
                        'message': "Access Denied: Operators and standard users are not authorized to access the Admin Panel."
                    }, status=403)

        response = self.get_response(request)
        return response
