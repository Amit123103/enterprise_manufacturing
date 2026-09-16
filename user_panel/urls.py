from django.urls import path
from user_panel import views

urlpatterns = [
    path('', views.dashboard_view, name='user_dashboard_root'),
    path('dashboard/', views.dashboard_view, name='user_dashboard'),
    path('my-products/', views.my_products_view, name='user_my_products'),
    path('products/', views.my_products_view, name='user_products_list'),
    path('products/<str:product_id>/', views.product_detail_view, name='user_product_detail'),

    # Bending
    path('bending/', views.bending_view, name='user_bending'),
    path('bending/<str:product_id>/submit/', views.bending_record_submit_view, name='user_bending_submit'),

    # Pressing
    path('pressing/', views.pressing_view, name='user_pressing'),
    path('pressing/<str:product_id>/<str:proc_type>/', views.pressing_record_submit_view, name='user_pressing_submit'),

    # Welding
    path('welding/', views.welding_view, name='user_welding'),
    path('welding/<str:product_id>/<int:stage_num>/', views.welding_stage_submit_view, name='user_welding_submit'),

    # Paint
    path('paint/', views.paint_view, name='user_paint'),
    path('paint/<str:product_id>/', views.paint_submit_view, name='user_paint_submit'),

    # PDI
    path('pdi/', views.pdi_view, name='user_pdi'),
    path('pdi/<str:product_id>/', views.pdi_submit_view, name='user_pdi_submit'),

    # Dispatch
    path('dispatch/', views.dispatch_view, name='user_dispatch'),
    path('dispatch/<str:product_id>/', views.dispatch_submit_view, name='user_dispatch_submit'),

    # Scanner & Docs
    path('scanner/', views.scanner_view, name='user_scanner'),
    path('documents/', views.documents_view, name='user_documents'),
]
