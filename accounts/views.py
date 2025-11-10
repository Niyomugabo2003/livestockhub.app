from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, LoginForm, UserUpdateForm, SellerProfileForm
from orders.models import Order

def custom_login(request):
    """Custom login view"""
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect('marketplace:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import authenticate
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect based on user type
                if hasattr(user, 'user_type'):
                    if user.user_type == 'seller':
                        return redirect('marketplace:seller_dashboard')
                    elif user.user_type == 'admin':
                        return redirect('dashboard:admin_dashboard')
                    else:  # customer
                        return redirect('marketplace:customer_dashboard')
                else:
                    return redirect('marketplace:home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def custom_logout(request):
    """Custom logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('marketplace:home')

def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect('marketplace:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            if user.user_type == 'seller':
                # For sellers, don't log them in immediately
                messages.success(request, 'Registration successful! Your seller account is pending admin approval. You will be notified once approved.')

                # Send notification to all admins
                from orders.models import Notification
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(user_type='admin')
                for admin in admins:
                    try:
                        Notification.objects.create(
                            user=admin,
                            notification_type='new_seller',
                            title='New Seller Registration',
                            message=f'New seller "{user.username}" has registered and is waiting for approval.',
                            related_order=None
                        )
                    except:
                        # If Notification model doesn't exist, skip notification
                        pass

                return redirect('marketplace:home')
            else:
                # For customers, log them in immediately
                login(request, user)
                messages.success(request, 'Registration successful! Welcome to LivestockHub.')
                return redirect('marketplace:customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    """User profile view"""
    from accounts.forms import PhoneForm

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
            user_form = UserUpdateForm(instance=request.user)
            seller_form = None
            if hasattr(request.user, 'user_type') and request.user.user_type == 'seller':
                seller_form = SellerProfileForm(instance=request.user.seller_profile)

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
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Please correct the error in the phone number.')

        else:
            # User form submission
            user_form = UserUpdateForm(request.POST, instance=request.user)
            phone_form = PhoneForm(initial={'phone': user_phone})
            seller_form = None
            if hasattr(request.user, 'user_type') and request.user.user_type == 'seller':
                seller_form = SellerProfileForm(request.POST, instance=request.user.seller_profile)

            if user_form.is_valid():
                user_form.save()
                if seller_form and seller_form.is_valid():
                    seller_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Please correct the errors below.')

    else:
        # GET request - initialize forms
        phone_form = PhoneForm(initial={'phone': user_phone})
        user_form = UserUpdateForm(instance=request.user)
        seller_form = None
        if hasattr(request.user, 'user_type') and request.user.user_type == 'seller':
            seller_form = SellerProfileForm(instance=request.user.seller_profile)

    # Get user statistics
    recent_orders = Order.objects.filter(customer=request.user).order_by('-created_at')[:5]
    total_orders = Order.objects.filter(customer=request.user).count()

    context = {
        'phone_form': phone_form,
        'user_form': user_form,
        'seller_form': seller_form,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'phone_set': phone_set,
        'user_phone': user_phone,
    }
    return render(request, 'accounts/profile.html', context)