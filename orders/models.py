from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    # Add payment choices
    PAYMENT_METHODS = (
        ('mtn', 'MTN Mobile Money'),
        ('paypal', 'PayPal'),
    )

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    
    # Payment fields
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='mtn')
    mtn_phone = models.CharField(max_length=15, blank=True)
    payment_status = models.CharField(
        max_length=20, 
        choices=(
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ), 
        default='pending'
    )
    
    # ADD CUSTOMER PHONE FIELD HERE
    customer_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Customer Phone",
        help_text="Customer's main contact number from their profile"
    )
    
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=15)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random
            import string
            self.order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # Auto-populate customer_phone from customer profile if not set
        if not self.customer_phone and hasattr(self.customer, 'profile'):
            self.customer_phone = self.customer.profile.phone
        
        super().save(*args, **kwargs)
    
    def get_payment_method_display_name(self):
        """Get human-readable payment method name"""
        return dict(self.PAYMENT_METHODS).get(self.payment_method, self.payment_method)
    
    def requires_mtn_phone(self):
        """Check if this order requires MTN phone number"""
        return self.payment_method == 'mtn'

    @property
    def seller_items(self):
        """Get all order items grouped by seller"""
        from django.db.models import Q
        sellers = User.objects.filter(
            Q(product__orderitem__order=self) & 
            Q(user_type='seller')
        ).distinct()
        
        seller_data = []
        for seller in sellers:
            items = self.items.filter(product__seller=seller)
            seller_data.append({
                'seller': seller,
                'items': items,
                'total': sum(item.quantity * item.price for item in items)
            })
        return seller_data
    

class OrderItem(models.Model):
    ORDER_ITEM_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('marketplace.Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=ORDER_ITEM_STATUS, default='pending')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} for {self.order.order_number}"

    @property
    def total_price(self):
        return self.quantity * self.price
        

    def can_update_status(self, new_status):
        """Check if status update is valid"""
        status_flow = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
        current_index = status_flow.index(self.status) if self.status in status_flow else -1
        new_index = status_flow.index(new_status) if new_status in status_flow else -1
        return new_index >= current_index

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('low_stock', 'Low Stock'),
        ('new_seller', 'New Seller Registration'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"