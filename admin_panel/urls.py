from django.urls import path
from admin_panel import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='admin_dashboard_root'),
    path('dashboard/', views.dashboard_view, name='admin_dashboard'),
    
    # Admin Management (Super Admin Only)
    path('admins/', views.admins_list_view, name='admins_list'),
    path('admins/create/', views.admin_create_view, name='admin_create'),
    path('admins/<int:admin_id>/toggle-status/', views.admin_toggle_status_view, name='admin_toggle_status'),
    path('admins/<int:admin_id>/authority/', views.admin_authority_view, name='admin_authority'),

    # User Management
    path('users/', views.users_list_view, name='users_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),

    # Product Registry
    path('products/', views.products_list_view, name='products_list'),
    path('products/create/', views.product_create_view, name='product_create'),
    path('products/<str:product_id>/', views.product_detail_view, name='product_detail'),

    # Production Oversight
    path('production/<str:stage_name>/', views.production_stage_view, name='admin_production_stage'),

    # Quality
    path('quality/', views.quality_management_view, name='quality_management'),
    path('quality/rejections/create/', views.rejection_create_view, name='rejection_create'),

    # Documents
    path('documents/', views.documents_view, name='documents_view'),
    path('documents/upload/', views.document_upload_view, name='document_upload'),

    # Reports
    path('reports/', views.reports_view, name='reports_view'),

    # Audit Logs
    path('audit-logs/', views.audit_logs_view, name='audit_logs_view'),

    # Scanner
    path('scanner/', views.admin_scanner_view, name='admin_scanner'),

    # System Settings
    path('settings/', views.settings_view, name='admin_settings'),
]
