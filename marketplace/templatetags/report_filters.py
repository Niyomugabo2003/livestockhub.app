# marketplace/templatetags/report_filters.py
from django import template

register = template.Library()

@register.filter
def get_chart_color(index):
    colors = ['primary', 'success', 'info', 'warning', 'danger', 'dark']
    return colors[index % len(colors)]

@register.filter
def get_status_badge(status):
    status_map = {
        'pending': 'warning',
        'confirmed': 'info', 
        'processing': 'primary',
        'shipped': 'info',
        'delivered': 'success',
        'cancelled': 'danger',
    }
    return status_map.get(status, 'secondary')

# Add safe product access filter
@register.filter
def get_product_display(order_item):
    """Safely access product information from order item"""
    if hasattr(order_item, 'product') and order_item.product:
        return f"{order_item.product.name} (x{order_item.quantity})"
    return "Product not available"