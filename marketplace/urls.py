from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Home and public pages
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),
    
    # Customer views
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/orders/', views.customer_orders, name='customer_orders'),
    
    # Seller views
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/products/add/', views.add_product, name='add_product'),
    path('seller/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('seller/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/orders/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('products/toggle-status/<int:product_id>/', views.toggle_product_status, name='toggle_product_status'),
    
    # Order status updates
    path('seller/orders/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('seller/orders/update-item-status/<int:item_id>/', views.update_order_item_status, name='update_order_item_status'),
    
    # Cart views - ADD BOTH cart AND view_cart for compatibility
    path('cart/', views.view_cart, name='cart'),  # Add this alias
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    
    # Category management
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    
    # API endpoints
    path('api/categories/search/', views.search_categories, name='search_categories'),
    path('api/categories/<int:category_id>/types/', views.get_category_types, name='get_category_types'),
    path('api/categories/<int:category_id>/subcategories/', views.get_subcategories, name='get_subcategories'),


     # Reporting URLs
    path('reports/seller/', views.seller_reports, name='seller_reports'),
    path('reports/admin/', views.admin_reports, name='admin_reports'),
    path('reports/generate-sales/', views.generate_sales_report, name='generate_sales_report'),
    path('reports/generate-admin/', views.generate_admin_report, name='generate_admin_report'),
]