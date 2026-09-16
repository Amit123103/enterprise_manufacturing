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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
