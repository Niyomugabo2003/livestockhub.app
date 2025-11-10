from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from accounts.models import User, SellerProfile
from marketplace.models import Category, Product
from orders.models import Order, OrderItem

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_seller_approved', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_seller_approved', 'is_active', 'date_joined']
    search_fields = ['username', 'email']
    actions = ['approve_sellers', 'unapprove_sellers', 'activate_users', 'deactivate_users']

    def approve_sellers(self, request, queryset):
        """Approve selected sellers"""
        updated = queryset.filter(user_type='seller').update(is_seller_approved=True)
        self.message_user(request, f"{updated} seller(s) approved successfully.")

        # Send notifications to approved sellers
        from orders.models import Notification
        for user in queryset.filter(user_type='seller'):
            try:
                Notification.objects.create(
                    user=user,
                    notification_type='order_confirmed',  # Using existing type
                    title='Seller Account Approved',
                    message='Congratulations! Your seller account has been approved. You can now access all seller features.',
                    related_order=None
                )
            except:
                pass  # Skip if notification fails
    approve_sellers.short_description = "Approve selected sellers"

    def unapprove_sellers(self, request, queryset):
        """Unapprove selected sellers"""
        updated = queryset.filter(user_type='seller').update(is_seller_approved=False)
        self.message_user(request, f"{updated} seller(s) unapproved successfully.")

        # Send notifications to unapproved sellers
        from orders.models import Notification
        for user in queryset.filter(user_type='seller'):
            try:
                Notification.objects.create(
                    user=user,
                    notification_type='order_cancelled',  # Using existing type
                    title='Seller Account Unapproved',
                    message='Your seller account has been unapproved. Please contact support for more information.',
                    related_order=None
                )
            except:
                pass  # Skip if notification fails
    unapprove_sellers.short_description = "Unapprove selected sellers"

    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated successfully.")
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated successfully.")
    deactivate_users.short_description = "Deactivate selected users"

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'rating', 'total_sales']
    search_fields = ['business_name', 'user__username']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_count', 'created_at']
    
    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'seller', 'category', 'price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['category', 'livestock_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'total_amount', 'status', 'created_at', 'view_order_link']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__username']
    list_editable = ['status']
    inlines = [OrderItemInline]
    
    def view_order_link(self, obj):
        url = reverse('dashboard:order_management')
        return format_html('<a href="{}">View in Dashboard</a>', url)
    view_order_link.short_description = 'Dashboard Link'

# Customize Admin Site
admin.site.site_header = "LivestockHub Administration"
admin.site.site_title = "LivestockHub Admin"
admin.site.index_title = "Welcome to LivestockHub Administration"