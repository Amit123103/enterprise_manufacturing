from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from apps.accounts.models import UserRole, UserStatus
from apps.audit.services import log_audit, AuditAction

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_admin_user:
            return redirect('admin_dashboard')
        return redirect('user_dashboard')

    if request.method == 'POST':
        login_identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=login_identifier, password=password)
        if not user:
            # Try by email if entered
            from apps.accounts.models import User
            try:
                user_obj = User.objects.get(email=login_identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user:
            if user.status == UserStatus.SUSPENDED:
                messages.error(request, "Your account has been suspended. Please contact the Super Admin.")
                return render(request, 'registration/login.html')
            if user.status == UserStatus.INACTIVE:
                messages.error(request, "Your account is inactive. Please contact your administrator.")
                return render(request, 'registration/login.html')

            login(request, user)
            log_audit(request, AuditAction.LOGIN, 'User', user.id, new_value=f"Login successful ({user.email})")

            messages.success(request, f"Welcome back, {user.full_name or user.username}!")
            if user.is_admin_user:
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid email/username or password. Please try again.")

    return render(request, 'registration/login.html')

def logout_view(request):
    if request.user.is_authenticated:
        log_audit(request, AuditAction.LOGOUT, 'User', request.user.id)
        logout(request)
        messages.info(request, "You have been logged out securely.")
    return redirect('login')
