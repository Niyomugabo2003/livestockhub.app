from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from accounts.models import User
from marketplace.models import Product, Category
from orders.models import Order
import json



def admin_required(function):
    """Decorator to ensure user is admin"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.user_type != 'admin':
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('marketplace:home')
        return function(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def admin_dashboard(request):
    """Redirect to Django admin or show custom dashboard"""
    # You can choose to redirect to Django admin or show custom dashboard
    # Option 1: Redirect to Django admin
    # return redirect('/admin/')
    
    # Option 2: Show custom dashboard (current implementation)
    total_users = User.objects.count()
    total_sellers = User.objects.filter(user_type='seller').count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_sellers = User.objects.filter(user_type='seller', is_seller_approved=False)
    
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    
    context = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_sellers': pending_sellers,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'pending_sellers_count': pending_sellers.count(),
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

@login_required
@admin_required
def admin_redirect(request):
    """Redirect to Django admin"""
    return redirect('/admin/')

# Keep other management views as they are...
@login_required
@admin_required
def user_management(request):
    """User management view"""
    users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = User.objects.get(id=user_id)
        
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            messages.success(request, f"User {user.username} {'activated' if user.is_active else 'deactivated'}")
        elif action == 'approve_seller' and user.user_type == 'seller':
            user.is_seller_approved = True
            user.save()

            # Send notification to the seller
            from orders.models import Notification
            try:
                Notification.objects.create(
                    user=user,
                    notification_type='order_confirmed',  # Using existing type, could add new one
                    title='Seller Account Approved',
                    message='Congratulations! Your seller account has been approved. You can now access all seller features.',
                    related_order=None
                )
            except:
                # If Notification model doesn't exist, skip notification
                pass

            messages.success(request, f"Seller {user.username} approved")
        
        return redirect('dashboard:user_management')
    
    context = {
        'users': users,
    }
    return render(request, 'dashboard/user_management.html', context)

@login_required
@admin_required
def seller_management(request):
    """Seller management view"""
    sellers = User.objects.filter(user_type='seller')
    
    if request.method == 'POST':
        seller_id = request.POST.get('seller_id')
        action = request.POST.get('action')
        seller = User.objects.get(id=seller_id)
        
        if action == 'toggle_approval':
            seller.is_seller_approved = not seller.is_seller_approved
            seller.save()
            status = "approved" if seller.is_seller_approved else "unapproved"
            messages.success(request, f"Seller {seller.username} {status}")
        
        return redirect('dashboard:seller_management')
    
    context = {
        'sellers': sellers,
    }
    return render(request, 'dashboard/seller_management.html', context)

@login_required
@admin_required
def product_management(request):
    """Product management view"""
    products = Product.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        product = Product.objects.get(id=product_id)
        
        if action == 'toggle_active':
            product.is_active = not product.is_active
            product.save()
            status = "activated" if product.is_active else "deactivated"
            messages.success(request, f"Product {product.name} {status}")
        
        return redirect('dashboard:product_management')
    
    context = {
        'products': products,
    }
    return render(request, 'dashboard/product_management.html', context)

@login_required
@admin_required
def order_management(request):
    """Order management view"""
    orders = Order.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        order = Order.objects.get(id=order_id)
        
        order.status = new_status
        order.save()
        messages.success(request, f"Order {order.order_number} status updated to {new_status}")
        
        return redirect('dashboard:order_management')
    
    context = {
        'orders': orders,
    }
    return render(request, 'dashboard/order_management.html', context)

