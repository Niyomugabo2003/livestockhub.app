from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem

@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)

@login_required
def my_orders(request):
    """User's order history"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'orders/my_orders.html', context)