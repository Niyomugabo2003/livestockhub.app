from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('admin-redirect/', views.admin_redirect, name='admin_redirect'),
    path('users/', views.user_management, name='user_management'),
    path('sellers/', views.seller_management, name='seller_management'),
    path('products/', views.product_management, name='product_management'),
    path('orders/', views.order_management, name='order_management'),
]