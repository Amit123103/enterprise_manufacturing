from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_admin_user:
        return redirect('admin_dashboard')
    return redirect('user_dashboard')

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', root_redirect, name='root_redirect'),
    path('dashboard-redirect/', root_redirect, name='dashboard_redirect'),
    
    # Auth endpoints
    path('', include('apps.accounts.urls')),
    
    # Dedicated isolated panels
    path('admin-panel/', include('admin_panel.urls')),
    path('user-panel/', include('user_panel.urls')),
]

# Always serve media if configured
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

def custom_500(request):
    import sys, traceback
    from django.http import HttpResponse
    exc_type, exc_val, exc_tb = sys.exc_info()
    tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb)) if exc_type else "No traceback available"
    print(f"[500 ERROR] {tb_str}", file=sys.stderr)
    return HttpResponse(f"""
    <!DOCTYPE html>
    <html>
    <head><title>System Diagnostic - 500 Error</title></head>
    <body style="font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f87171; padding: 30px;">
        <h1 style="color: #ef4444; font-size: 22px;">System Diagnostic - 500 Error</h1>
        <p style="color: #94a3b8; font-size: 14px;">A runtime exception occurred while processing this request:</p>
        <pre style="background: #1e293b; color: #fca5a5; padding: 18px; border-radius: 8px; font-size: 13px; overflow-x: auto; border: 1px solid #334155;">{tb_str}</pre>
    </body>
    </html>
    """, status=500)

handler500 = 'config.urls.custom_500'

