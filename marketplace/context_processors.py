from .models import Cart

def cart_item_count(request):
    """Add cart item count to all templates"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return {'cart_item_count': cart.total_items}
        except Cart.DoesNotExist:
            return {'cart_item_count': 0}
    return {'cart_item_count': 0}