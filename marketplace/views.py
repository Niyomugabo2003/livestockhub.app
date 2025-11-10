from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Product, Category, Cart, CartItem
from .forms import ProductForm, ProductSearchForm, CheckoutForm, CategoryForm
from orders.models import Order, OrderItem, Notification
import json
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


def home(request):
    """Home page with featured products and categories"""
    categories = Category.objects.filter(parent__isnull=True, is_active=True)[:6]
    featured_products = Product.objects.filter(is_active=True)[:8]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
    }
    return render(request, 'marketplace/home.html', context)

@login_required
def customer_dashboard(request):
    """Customer dashboard view"""
    # Allow access to customers and also handle edge cases
    if hasattr(request.user, 'user_type'):
        if request.user.user_type == 'seller':
            messages.info(request, "Redirected to seller dashboard.")
            return redirect('marketplace:seller_dashboard')
        elif request.user.user_type == 'admin':
            messages.info(request, "Redirected to admin dashboard.")
            return redirect('dashboard:admin_dashboard')
        elif request.user.user_type not in ['customer', '']:
            messages.error(request, "Access denied. Customer account required.")
            return redirect('marketplace:home')
    
    # Check if phone is set
    phone_set = False
    if request.session.get('user_phone'):
        phone_set = True
    else:
        # Check if user has any orders with phone numbers
        has_orders_with_phone = Order.objects.filter(
            customer=request.user
        ).exclude(customer_phone='').exists()
        phone_set = has_orders_with_phone
    
    # Get customer's recent orders
    recent_orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:5]
    
    # Get customer's cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    # Get recommended products
    ordered_categories = OrderItem.objects.filter(
        order__customer=request.user
    ).values_list('product__category', flat=True).distinct()
    
    recommended_products = Product.objects.filter(
        category__in=ordered_categories,
        is_active=True
    ).exclude(
        orderitem__order__customer=request.user
    )[:4]
    
    if not recommended_products:
        recommended_products = Product.objects.filter(is_active=True)[:4]
    
    context = {
        'recent_orders': recent_orders,
        'cart_items': cart_items,
        'cart': cart,
        'recommended_products': recommended_products,
        'phone_set': phone_set,
    }
    return render(request, 'marketplace/customer_dashboard.html', context)

@login_required
def seller_dashboard(request):
    """Seller dashboard view"""
    if request.user.user_type != 'seller' and not request.user.is_staff:
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You will be able to access your dashboard once approved.")
        return redirect('marketplace:home')
    
    # Get seller's products
    seller_products = Product.objects.filter(seller=request.user)
    total_products = seller_products.count()
    active_products = seller_products.filter(is_active=True).count()
    
    # Low stock products (less than 10 items)
    low_stock_products = seller_products.filter(stock_quantity__lt=10)
    
    # Calculate both TOTAL SALES (count) and TOTAL REVENUE (money) from DELIVERED orders
    from django.db.models.functions import Coalesce
    from django.db.models import F, DecimalField

    sales_data = OrderItem.objects.filter(
        product__seller=request.user,
        order__status='delivered'  # Only count delivered orders
    ).aggregate(
        total_items_sold=Coalesce(Sum('quantity'), 0),
        total_revenue=Coalesce(
            Sum(F('quantity') * F('price'), output_field=DecimalField(max_digits=12, decimal_places=2)),
            Decimal('0.00')
        )
    )
    
    total_sales = sales_data['total_items_sold'] or 0
    total_revenue = sales_data['total_revenue'] or Decimal('0.00')
    
    # Use total_sales as monetary amount
    total_sales = total_revenue
    
    # Count total delivered orders
    total_orders = Order.objects.filter(
        items__product__seller=request.user,
        status='delivered'
    ).distinct().count()
    
    # Calculate business rating (default to 0.0 if no rating system)
    business_rating = 0.0
    
    # Recent orders (last 5 orders - include all statuses for display)
    recent_orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-created_at')[:5]
    
    # Recent products
    recent_products = Product.objects.filter(seller=request.user).order_by('-created_at')[:5]
    
    context = {
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'business_rating': business_rating,
        'recent_orders': recent_orders,
        'recent_products': recent_products,
    }
    return render(request, 'marketplace/seller_dashboard.html', context)

@login_required
def seller_orders(request):
    """View orders for seller's products"""
    if request.user.user_type != 'seller' and not request.user.is_staff:
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval.")
        return redirect('marketplace:home')
    
    # Get orders that contain seller's products
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-created_at')
    
    # Calculate order statistics
    pending_orders = orders.filter(status='pending').count()
    processing_orders = orders.filter(status__in=['confirmed', 'processing', 'shipped']).count()
    delivered_orders = orders.filter(status='delivered').count()
    
    context = {
        'orders': orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'delivered_orders': delivered_orders,
    }
    return render(request, 'marketplace/seller_orders.html', context)

@login_required
def update_order_status(request, order_id):
    """Update order status (for sellers)"""
    if request.user.user_type != 'seller' and not request.user.is_staff:
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval.")
        return redirect('marketplace:home')
    
    order = get_object_or_404(Order, id=order_id, items__product__seller=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # Define valid statuses
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        
        if new_status in valid_statuses:
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Create notification for customer
            try:
                Notification.objects.create(
                    user=order.customer,
                    notification_type=f'order_{new_status}',
                    title=f"Order Status Updated",
                    message=f"Your order #{order.order_number} status changed from {old_status} to {new_status}",
                    related_order=order
                )
            except:
                # If Notification model doesn't exist, skip notification
                pass
            
            messages.success(request, f"Order status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status.")
    
    return redirect('marketplace:seller_order_detail', order_id=order.id)

@login_required
def update_order_item_status(request, item_id):
    """Update individual order item status (for sellers)"""
    if request.user.user_type != 'seller' and not request.user.is_staff:
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval.")
        return redirect('marketplace:home')
    
    order_item = get_object_or_404(OrderItem, id=item_id, product__seller=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status in dict(OrderItem.ORDER_ITEM_STATUS):
            old_status = order_item.status
            order_item.status = new_status
            order_item.save()
            
            # Create notification for customer
            Notification.objects.create(
                user=order_item.order.customer,
                notification_type=f'order_{new_status}',
                title=f"Order Item Status Updated",
                message=f"Your {order_item.product.name} status changed from {old_status} to {new_status}",
                related_order=order_item.order
            )
            
            messages.success(request, f"Order item status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status.")
    
    return redirect('marketplace:seller_order_detail', order_id=order_item.order.id)

@login_required
def customer_orders(request):
    """Customer order history"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'marketplace/customer_orders.html', context)

@login_required
def manage_categories(request):
    """Manage categories (for admin/sellers)"""
    if not request.user.is_staff and request.user.user_type != 'seller':
        messages.error(request, "Access denied.")
        return redirect('marketplace:home')

    # Check if seller is approved (only for sellers, not admins)
    if request.user.user_type == 'seller' and not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot manage categories yet.")
        return redirect('marketplace:home')
    
    categories = Category.objects.filter(is_active=True).order_by('parent__name', 'name')
    parent_categories = Category.objects.filter(parent__isnull=True, is_active=True)
    
    # Annotate categories with product count
    categories = categories.annotate(product_count=Count('product'))
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully!")
            return redirect('marketplace:manage_categories')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm()
    
    context = {
        'categories': categories,
        'parent_categories': parent_categories,
        'form': form,
    }
    return render(request, 'marketplace/manage_categories.html', context)

def product_list(request):
    """List all active products with filtering"""
    products = Product.objects.filter(is_active=True)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        category = get_object_or_404(Category, id=category_id, is_active=True)
        # Get all subcategories and include them in the filter
        subcategories = category.get_all_subcategories()
        all_categories = [category] + subcategories
        products = products.filter(category__in=all_categories)
    
    # Filter by livestock type
    livestock_type = request.GET.get('livestock_type')
    if livestock_type:
        products = products.filter(livestock_type=livestock_type)
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Price range filtering
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    categories = Category.objects.filter(parent__isnull=True, is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'livestock_types': Product.LIVESTOCK_TYPES,
    }
    return render(request, 'marketplace/product_list.html', context)

def product_detail(request, product_id):
    """Product detail view"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, 
        is_active=True
    ).exclude(id=product_id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'marketplace/product_detail.html', context)

def get_category_types(request, category_id):
    """API endpoint to get category types/subcategories"""
    category = get_object_or_404(Category, id=category_id, is_active=True)
    subcategories = category.subcategories.filter(is_active=True)
    
    types = [
        {
            'id': subcat.id,
            'name': subcat.name,
            'has_subcategories': subcat.has_subcategories
        }
        for subcat in subcategories
    ]
    
    return JsonResponse({'types': types})

@login_required
def seller_order_detail(request, order_id):
    """View detailed information about a specific order"""
    if request.user.user_type != 'seller' and not request.user.is_staff:
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval.")
        return redirect('marketplace:home')
    
    # Get order with items that belong to the current seller
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        id=order_id,
        items__product__seller=request.user
    )
    
    # Filter order items to only show seller's products
    seller_order_items = order.items.filter(product__seller=request.user)
    
    context = {
        'order': order,
        'seller_order_items': seller_order_items,
        'order_total': sum(item.quantity * item.price for item in seller_order_items),
        'order_item_statuses': OrderItem.ORDER_ITEM_STATUS,
    }
    return render(request, 'marketplace/seller_order_detail.html', context)

def search_categories(request):
    """API endpoint to search categories"""
    query = request.GET.get('q', '')
    if query:
        categories = Category.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query),
            is_active=True
        )[:10]
        results = [
            {
                'id': category.id,
                'name': category.name,
                'full_path': category.get_full_path(),
                'has_subcategories': category.has_subcategories
            }
            for category in categories
        ]
    else:
        results = []
    
    return JsonResponse({'results': results})

def get_subcategories(request, category_id):
    """API endpoint to get subcategories for a category"""
    category = get_object_or_404(Category, id=category_id, is_active=True)
    subcategories = category.subcategories.filter(is_active=True)
    
    results = [
        {
            'id': subcat.id,
            'name': subcat.name,
            'has_subcategories': subcat.has_subcategories
        }
        for subcat in subcategories
    ]
    
    return JsonResponse({
        'category_name': category.name,
        'subcategories': results
    })

@login_required
def add_product(request):
    """Add new product with category handling"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot add products yet.")
        return redirect('marketplace:home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                product = form.save()
                messages.success(request, "Product added successfully!")
                return redirect('marketplace:seller_products')

            except Exception as e:
                messages.error(request, f"Error saving product: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(user=request.user)
    
    # Get parent categories for the form
    parent_categories = Category.objects.filter(parent__isnull=True, is_active=True)
    
    context = {
        'form': form,
        'parent_categories': parent_categories,
    }
    return render(request, 'marketplace/add_product.html', context)

@login_required
def edit_product(request, product_id):
    """Edit existing product"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot edit products yet.")
        return redirect('marketplace:home')

    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully!")
            return redirect('marketplace:seller_products')
    else:
        form = ProductForm(instance=product, user=request.user)
    
    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'marketplace/edit_product.html', context)

@login_required
def delete_product(request, product_id):
    """Delete product"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot delete products yet.")
        return redirect('marketplace:home')

    product = get_object_or_404(Product, id=product_id, seller=request.user)

    if request.method == 'POST':
        # Check if product has any related orders
        from orders.models import OrderItem
        if OrderItem.objects.filter(product=product).exists():
            messages.error(request, f'Cannot delete product "{product.name}" because it has existing orders. Deactivate it instead.')
            return redirect('marketplace:seller_products')

        product_name = product.name  # Store name before deletion
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('marketplace:seller_products')

    return render(request, 'marketplace/delete_product.html', {'product': product})

@login_required
def seller_products(request):
    """View seller's products with search and filter functionality"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot manage products yet.")
        return redirect('marketplace:home')

    products = Product.objects.filter(seller=request.user)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)

    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category_id=category_filter)

    # Filter by stock level
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lt=10)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sort_fields = ['name', '-name', 'price', '-price', 'stock_quantity', '-stock_quantity', 'created_at', '-created_at']
    if sort_by in valid_sort_fields:
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-created_at')

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(products, 20)  # Show 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories for filter dropdown
    categories = Category.objects.filter(
        Q(product__seller=request.user)
    ).distinct().order_by('name')

    # Statistics
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    inactive_products = products.filter(is_active=False).count()
    low_stock_products = products.filter(stock_quantity__lt=10).count()

    context = {
        'products': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': categories,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'sort_by': sort_by,
        'total_products': total_products,
        'active_products': active_products,
        'inactive_products': inactive_products,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'marketplace/seller_products.html', context)

def category_products(request, category_id):
    """Display products by category including subcategories"""
    category = get_object_or_404(Category, id=category_id, is_active=True)
    
    # Get all subcategories and include them in the filter
    subcategories = category.get_all_subcategories()
    all_categories = [category] + subcategories
    
    products = Product.objects.filter(category__in=all_categories, is_active=True)
    
    context = {
        'category': category,
        'products': products,
        'subcategories': subcategories,
    }
    return render(request, 'marketplace/category_products.html', context)

# Cart Views
@login_required
def view_cart(request):
    """View user's cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    context = {
        'cart': cart,
    }
    return render(request, 'marketplace/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get quantity from POST data, default to 1 if not provided
    quantity = int(request.POST.get('quantity', 1))

    # Validate quantity
    if quantity < 1:
        quantity = 1
    elif quantity > product.stock_quantity:
        quantity = product.stock_quantity

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity += quantity
        # Ensure we don't exceed stock
        if cart_item.quantity > product.stock_quantity:
            cart_item.quantity = product.stock_quantity
        cart_item.save()

    messages.success(request, f"Added {cart_item.quantity} x {product.name} to cart!")
    return redirect('marketplace:view_cart')

@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated!")
        else:
            cart_item.delete()
            messages.success(request, "Item removed from cart!")
    
    return redirect('marketplace:view_cart')

@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart!")
    return redirect('marketplace:view_cart')

# Checkout Views
@login_required
def checkout(request):
    """Checkout process"""
    cart = get_object_or_404(Cart, user=request.user)
    
    if cart.total_items == 0:
        messages.error(request, "Your cart is empty!")
        return redirect('marketplace:view_cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # Get all form data
                payment_method = form.cleaned_data['payment_method']
                mtn_phone = form.cleaned_data.get('mtn_phone', '')
                customer_phone = form.cleaned_data.get('customer_phone', '')
                shipping_phone = form.cleaned_data.get('shipping_phone', '')

                # Save phone to session for profile completion
                if customer_phone:
                    request.session['user_phone'] = customer_phone
                    request.session.modified = True

                # Create order
                order = Order.objects.create(
                    customer=request.user,
                    total_amount=cart.total_price,
                    shipping_address=form.cleaned_data['shipping_address'],
                    shipping_city=form.cleaned_data['shipping_city'],
                    shipping_phone=shipping_phone,  # This is the delivery phone for sellers to call
                    customer_phone=customer_phone,  # This is the main customer phone
                    notes=form.cleaned_data.get('notes', ''),
                    payment_method=payment_method,
                    mtn_phone=mtn_phone if payment_method == 'mtn' else ''
                )

                # Create order items and reduce stock
                for cart_item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price
                    )
                    cart_item.product.reduce_stock(cart_item.quantity)

                # Clear cart
                cart.items.all().delete()

                # Payment-specific success messages
                if payment_method == 'mtn':
                    messages.success(request, f"Order #{order.order_number} placed successfully! You will receive an MTN Mobile Money prompt on {mtn_phone}.")
                elif payment_method == 'paypal':
                    messages.success(request, f"Order #{order.order_number} placed successfully! You will be redirected to PayPal for payment.")
                else:
                    messages.success(request, f"Order #{order.order_number} placed successfully!")

                return redirect('marketplace:order_confirmation', order_id=order.id)

            except Exception as e:
                messages.error(request, f"Error processing order: {str(e)}")
                context = {'cart': cart, 'form': form}
                return render(request, 'marketplace/checkout.html', context)
        else:
            # Form is not valid, show errors
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill form with available data
        initial_data = {}
        
        # Get phone from session or previous orders
        if request.session.get('user_phone'):
            initial_data['customer_phone'] = request.session['user_phone']
            # For shipping phone, use the same OR leave empty for customer to specify different delivery phone
            initial_data['shipping_phone'] = ''  # Leave empty so customer can enter specific delivery phone
        else:
            # Try to get phone from most recent order
            recent_order = Order.objects.filter(customer=request.user).exclude(customer_phone='').order_by('-created_at').first()
            if recent_order and recent_order.customer_phone:
                initial_data['customer_phone'] = recent_order.customer_phone
                initial_data['shipping_phone'] = ''  # Leave empty for delivery phone
                request.session['user_phone'] = recent_order.customer_phone
            else:
                # No phone found - both fields will be empty
                initial_data['customer_phone'] = ''
                initial_data['shipping_phone'] = ''
        
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'cart': cart,
        'form': form,
    }
    return render(request, 'marketplace/checkout.html', context)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'marketplace/order_confirmation.html', context)

@login_required
def toggle_product_status(request, product_id):
    """Toggle product active/inactive status"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot manage products yet.")
        return redirect('marketplace:home')

    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save()
        
        status = "activated" if product.is_active else "deactivated"
        messages.success(request, f'Product "{product.name}" has been {status} successfully.')
    
    return redirect('marketplace:seller_products')

# Essential pages
def about(request):
    return render(request, 'marketplace/about.html')

def contact(request):
    return render(request, 'marketplace/contact.html')

def help_center(request):
    return render(request, 'marketplace/help_center.html')

def privacy_policy(request):
    return render(request, 'marketplace/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'marketplace/terms_of_service.html')

def sitemap(request):
    return render(request, 'marketplace/sitemap.html')

# Reporting Views
@login_required
def seller_reports(request):
    """Seller reporting dashboard with real data"""
    if request.user.user_type != 'seller':
        messages.error(request, "Access denied. Seller account required.")
        return redirect('marketplace:home')

    # Check if seller is approved
    if not request.user.is_seller_approved:
        messages.warning(request, "Your seller account is pending admin approval. You cannot view reports yet.")
        return redirect('marketplace:home')

    # Calculate date ranges
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    
    # Get seller's products
    seller_products = Product.objects.filter(seller=request.user)
    
    # Get orders for this seller
    seller_orders = Order.objects.filter(
        items__product__in=seller_products
    ).distinct()
    
    # Recent orders (last 30 days)
    recent_orders = seller_orders.filter(created_at__date__gte=thirty_days_ago)
    
    # Calculate metrics
    total_revenue = recent_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    total_orders = recent_orders.count()
    
    # Calculate products sold
    products_sold = OrderItem.objects.filter(
        order__in=recent_orders,
        product__in=seller_products
    ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0
    
    avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
    
    # Top products
    top_products = OrderItem.objects.filter(
        order__in=recent_orders,
        product__in=seller_products
    ).values(
        'product__name',
        'product__id'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_sold')[:5]
    
    # Revenue by month (last 6 months)
    revenue_by_month = []
    for i in range(6):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        monthly_revenue = seller_orders.filter(
            created_at__date__range=[month_start, month_end]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        revenue_by_month.append({
            'month': month_start.strftime('%b'),
            'revenue': float(monthly_revenue)
        })
    
    revenue_by_month.reverse()
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'products_sold': products_sold,
        'avg_order_value': avg_order_value,
        'top_products': top_products,
        'revenue_by_month': revenue_by_month,
        'recent_orders': recent_orders[:5],
    }
    return render(request, 'marketplace/seller_reports.html', context)

@login_required
def admin_reports(request):
    """Admin reporting dashboard with real data"""
    # Check if user is admin/staff
    if not request.user.is_staff:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('marketplace:home')
    
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Platform metrics
    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    total_orders = Order.objects.count()
    
    # User metrics
    from django.contrib.auth.models import User
    total_users = User.objects.count()
    active_users = User.objects.filter(
        last_login__date__gte=thirty_days_ago
    ).count()
    
    # Product metrics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(stock_quantity__lt=10).count()
    
    # Seller metrics
    active_sellers = User.objects.filter(
        products__isnull=False,
        last_login__date__gte=thirty_days_ago
    ).distinct().count()
    
    # Revenue by category
    revenue_by_category = OrderItem.objects.values(
        'product__category__name'
    ).annotate(
        revenue=Sum('price'),
        orders=Count('order')
    ).order_by('-revenue')[:6]
    
    # Top sellers
    top_sellers = User.objects.filter(
        products__order_items__isnull=False
    ).annotate(
        total_revenue=Sum('products__order_items__price'),
        total_orders=Count('products__order_items__order', distinct=True),
        avg_rating=Avg('products__reviews__rating')
    ).filter(
        total_revenue__isnull=False
    ).order_by('-total_revenue')[:5]
    
    # Recent platform activity
    recent_orders = Order.objects.select_related('customer').order_by('-created_at')[:5]
    new_sellers = User.objects.filter(
        products__isnull=False,
        date_joined__date__gte=thirty_days_ago
    ).distinct()[:3]
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_users': total_users,
        'active_users': active_users,
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'active_sellers': active_sellers,
        'revenue_by_category': revenue_by_category,
        'top_sellers': top_sellers,
        'recent_orders': recent_orders,
        'new_sellers': new_sellers,
    }
    return render(request, 'marketplace/admin_reports.html', context)

@login_required
def generate_sales_report(request):
    """Generate sales report for seller"""
    if request.user.user_type != 'seller':
        return JsonResponse({'success': False, 'error': 'Access denied'})

    # Check if seller is approved
    if not request.user.is_seller_approved:
        return JsonResponse({'success': False, 'error': 'Account pending approval'})

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        report_type = request.POST.get('report_type', 'sales')
        
        # Get seller's orders in date range
        seller_products = Product.objects.filter(seller=request.user)
        orders = Order.objects.filter(
            items__product__in=seller_products,
            created_at__date__range=[start_date, end_date]
        ).distinct()
        
        # Calculate metrics
        total_sales = orders.count()
        total_revenue = sum(order.total_amount for order in orders)
        average_order_value = total_revenue / total_sales if total_sales > 0 else 0
        
        # Top products
        top_products = OrderItem.objects.filter(
            order__in=orders,
            product__in=seller_products
        ).values('product__name').annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('price')
        ).order_by('-total_sold')[:5]
        
        return JsonResponse({
            'success': True, 
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'average_order_value': float(average_order_value),
            'top_products': list(top_products)
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def generate_admin_report(request):
    """Generate admin reports"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Access denied'})
        
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        report_type = request.POST.get('report_type', 'revenue')
        
        if report_type == 'revenue':
            orders = Order.objects.filter(created_at__date__range=[start_date, end_date])
            total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            total_orders = orders.count()
            
            data = {
                'total_revenue': float(total_revenue),
                'total_orders': total_orders,
                'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0
            }
        elif report_type == 'users':
            from django.contrib.auth.models import User
            new_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
            data = {'new_users': new_users}
        else:
            data = {}
        
        return JsonResponse({'success': True, 'data': data})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# Profile view (add this if it doesn't exist)

@login_required
def profile(request):
    """User profile management"""
    from django.contrib.auth.forms import UserChangeForm
    from .forms import PhoneForm
    
    # Initialize variables
    phone_set = False
    user_phone = request.session.get('user_phone', '')
    
    # Check if phone is set in session or in recent orders
    if user_phone:
        phone_set = True
    else:
        # Check if user has any orders with phone numbers
        recent_order_with_phone = Order.objects.filter(
            customer=request.user
        ).exclude(customer_phone='').order_by('-created_at').first()
        if recent_order_with_phone:
            user_phone = recent_order_with_phone.customer_phone
            request.session['user_phone'] = user_phone
            phone_set = True
    
    # Handle form submission
    if request.method == 'POST':
        # Check which form was submitted
        if 'phone' in request.POST:
            # Phone form submission
            phone_form = PhoneForm(request.POST)
            user_form = UserChangeForm(instance=request.user)
            
            if phone_form.is_valid():
                phone = phone_form.cleaned_data['phone']
                
                # Store phone in session
                request.session['user_phone'] = phone
                request.session.modified = True
                
                # Update any recent orders without phone numbers
                orders_without_phone = Order.objects.filter(
                    customer=request.user,
                    customer_phone=''
                )
                for order in orders_without_phone:
                    order.customer_phone = phone
                    order.save()
                
                phone_set = True
                user_phone = phone
                messages.success(request, 'Phone number saved successfully! Your profile is now complete.')
                return redirect('marketplace:profile')
            else:
                messages.error(request, 'Please correct the error in the phone number.')
        
        else:
            # User form submission
            phone_form = PhoneForm(initial={'phone': user_phone})
            user_form = UserChangeForm(request.POST, instance=request.user)
            
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('marketplace:profile')
            else:
                messages.error(request, 'Please correct the errors below.')
    
    else:
        # GET request - initialize forms
        phone_form = PhoneForm(initial={'phone': user_phone})
        user_form = UserChangeForm(instance=request.user)
    
    # Get user statistics
    recent_orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:5]
    total_orders = Order.objects.filter(customer=request.user).count()
    
    context = {
        'phone_form': phone_form,
        'user_form': user_form,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'phone_set': phone_set,
        'user_phone': user_phone,
    }
    return render(request, 'marketplace/profile.html', context)
