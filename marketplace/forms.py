from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
from .models import Product, Category
from orders.models import Order

class UserProfileForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field
        if 'password' in self.fields:
            del self.fields['password']
        
        # Add Bootstrap classes and placeholders to form fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your username'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })

class PhoneForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+250789123456 or 0789123456',
        }),
        help_text="Required for order updates, delivery coordination, and account security"
    )
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Basic phone validation
            import re
            # Remove any non-digit characters except +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)
            
            # Check if it's a valid Rwandan phone number format
            if not re.match(r'^(\+?250|0)?[7][0-9]{8}$', cleaned_phone):
                raise forms.ValidationError("Please enter a valid Rwandan phone number (e.g., +250789123456 or 0789123456)")
            
            # Format to standard format
            if cleaned_phone.startswith('0'):
                cleaned_phone = '+25' + cleaned_phone[1:]
            elif cleaned_phone.startswith('250'):
                cleaned_phone = '+' + cleaned_phone
            elif not cleaned_phone.startswith('+'):
                cleaned_phone = '+25' + cleaned_phone
            
            return cleaned_phone
        return phone

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'parent', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter category description'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Category Name',
            'description': 'Description',
            'parent': 'Parent Category (Optional)',
            'image': 'Category Image',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check if category with same name already exists (case insensitive)
            existing_category = Category.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing_category = existing_category.exclude(pk=self.instance.pk)
            if existing_category.exists():
                raise ValidationError("A category with this name already exists.")
        return name

class ProductForm(forms.ModelForm):
    category_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search for existing category...',
            'id': 'category-search'
        }),
        label='Search Category'
    )
    
    new_category_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Or enter new category name...',
            'id': 'new-category-name'
        }),
        label='New Category Name'
    )
    
    parent_category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'parent-category'}),
        label='Parent Category (Optional)'
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'stock_quantity', 'livestock_type', 'animal_type', 'image', 'image2', 'image3']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'category-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter product description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price in RWF'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter available quantity'}),
            'livestock_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_livestock_type',
                'hx-get': '/marketplace/get-animal-types/',
                'hx-target': '#id_animal_type',
                'hx-trigger': 'change'
            }),
            'animal_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_animal_type'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control-file', 'style': 'display: none;'}),
            'image2': forms.FileInput(attrs={'class': 'form-control-file', 'style': 'display: none;'}),
            'image3': forms.FileInput(attrs={'class': 'form-control-file', 'style': 'display: none;'}),
        }
        labels = {
            'name': 'Product Name',
            'category': 'Select Existing Category',
            'description': 'Description',
            'price': 'Price (RWF)',
            'stock_quantity': 'Stock Quantity',
            'livestock_type': 'Livestock Type',
            'animal_type': 'Animal Type',
            'image': 'Primary Product Image',
            'image2': 'Additional Product Image 1',
            'image3': 'Additional Product Image 2',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Get the user from form initialization
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        
        # Set initial values for edit mode
        if self.instance and self.instance.pk:
            if self.instance.category:
                self.fields['category_search'].initial = self.instance.category.name
                if self.instance.category.parent:
                    self.fields['parent_category'].initial = self.instance.category.parent
            
            # Set dynamic animal_type choices based on current livestock_type
            if self.instance.livestock_type:
                choices = self.instance.get_animal_type_choices()
                self.fields['animal_type'].choices = [('', '---------')] + list(choices)
        else:
            # For new products, start with empty animal_type choices
            self.fields['animal_type'].choices = [('', '---------')]

    def save(self, commit=True):
        # Set the seller to the current user if it's a new product
        if not self.instance.pk and self.user:
            self.instance.seller = self.user
        return super().save(commit)

    def clean(self):
        cleaned_data = super().clean()
        category_search = cleaned_data.get('category_search')
        new_category_name = cleaned_data.get('new_category_name')
        selected_category = cleaned_data.get('category')
        parent_category = cleaned_data.get('parent_category')
        livestock_type = cleaned_data.get('livestock_type')
        animal_type = cleaned_data.get('animal_type')

        # Validate category selection
        if not selected_category and not new_category_name:
            raise ValidationError({
                'category_search': 'Please either select an existing category or create a new one.',
                'new_category_name': 'Please either select an existing category or create a new one.'
            })

        if selected_category and new_category_name:
            raise ValidationError({
                'new_category_name': 'Please choose either an existing category or create a new one, not both.'
            })

        # Handle new category creation
        if new_category_name:
            # Check if category already exists
            existing_category = Category.objects.filter(name__iexact=new_category_name, is_active=True).first()
            if existing_category:
                cleaned_data['category'] = existing_category
            else:
                # Create new category
                new_category = Category.objects.create(
                    name=new_category_name,
                    parent=parent_category,
                    description=f"Category for {new_category_name}"
                )
                cleaned_data['category'] = new_category

        # Validate animal_type based on livestock_type
        if livestock_type and animal_type:
            # Create temporary product instance to validate animal_type
            temp_product = Product(livestock_type=livestock_type)
            valid_choices = dict(temp_product.get_animal_type_choices())
            if animal_type not in valid_choices:
                raise ValidationError({
                    'animal_type': f'Invalid animal type for {livestock_type}. Please select a valid option.'
                })

        return cleaned_data

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_stock_quantity(self):
        stock_quantity = self.cleaned_data.get('stock_quantity')
        if stock_quantity and stock_quantity < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock_quantity

    def clean_animal_type(self):
        livestock_type = self.cleaned_data.get('livestock_type')
        animal_type = self.cleaned_data.get('animal_type')
        
        # If livestock_type is selected but animal_type is not, require it
        if livestock_type and not animal_type:
            raise forms.ValidationError("Please select an animal type for the chosen livestock type.")
        
        return animal_type

class ProductSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    livestock_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Product.LIVESTOCK_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    animal_type = forms.ChoiceField(
        choices=[('', 'All Animal Types')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'search-animal-type'})
    )
    
    min_price = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price'
        })
    )
    
    max_price = forms.DecimalField(
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update animal_type choices based on livestock_type if provided in initial data
        if 'livestock_type' in self.data:
            try:
                livestock_type = self.data.get('livestock_type')
                if livestock_type:
                    product = Product(livestock_type=livestock_type)
                    choices = product.get_animal_type_choices()
                    self.fields['animal_type'].choices = [('', 'All Animal Types')] + list(choices)
            except (ValueError, TypeError):
                pass

class CheckoutForm(forms.ModelForm):
    customer_phone = forms.CharField(
        max_length=20,
        required=True,
        label="Customer Phone Number",
        help_text="Your main contact number for order updates and seller communication"
    )
    shipping_phone = forms.CharField(
        max_length=20,
        required=False,
        label="Delivery Contact Phone (Optional)",
        help_text="Different number for delivery contact if needed"
    )
    mtn_phone = forms.CharField(
        max_length=15,
        required=False,
        label="MTN Mobile Money Phone",
        help_text="Your MTN phone number for payment"
    )

    class Meta:
        model = Order
        fields = ['shipping_address', 'shipping_city', 'shipping_phone', 'customer_phone', 'notes', 'payment_method']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make mtn_phone required conditionally based on payment method
        self.fields['mtn_phone'].required = False

        # Add Bootstrap classes to all fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control'
            })

        # Add placeholders
        self.fields['shipping_address'].widget.attrs.update({
            'placeholder': 'Enter your full delivery address',
            'rows': 3
        })
        self.fields['shipping_city'].widget.attrs.update({
            'placeholder': 'Enter city name'
        })
        self.fields['customer_phone'].widget.attrs.update({
            'placeholder': '+250789123456 or 0789123456'
        })
        self.fields['shipping_phone'].widget.attrs.update({
            'placeholder': '+250789123456 or 0789123456 (optional)'
        })
        self.fields['notes'].widget.attrs.update({
            'placeholder': 'Any special delivery instructions...',
            'rows': 2
        })

    def clean_customer_phone(self):
        phone = self.cleaned_data.get('customer_phone')
        if phone:
            # Basic phone validation
            import re
            # Remove any non-digit characters except +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)

            # Check if it's a valid Rwandan phone number format
            if not re.match(r'^(\+?250|0)?[7][0-9]{8}$', cleaned_phone):
                raise forms.ValidationError("Please enter a valid Rwandan phone number (e.g., +250789123456 or 0789123456)")

            # Format to standard format
            if cleaned_phone.startswith('0'):
                cleaned_phone = '+25' + cleaned_phone[1:]
            elif cleaned_phone.startswith('250'):
                cleaned_phone = '+' + cleaned_phone
            elif not cleaned_phone.startswith('+'):
                cleaned_phone = '+25' + cleaned_phone

            return cleaned_phone
        return phone

    def clean_shipping_phone(self):
        phone = self.cleaned_data.get('shipping_phone')
        if phone:
            # Basic phone validation
            import re
            # Remove any non-digit characters except +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)

            # Check if it's a valid Rwandan phone number format
            if not re.match(r'^(\+?250|0)?[7][0-9]{8}$', cleaned_phone):
                raise forms.ValidationError("Please enter a valid Rwandan phone number (e.g., +250789123456 or 0789123456)")

            # Format to standard format
            if cleaned_phone.startswith('0'):
                cleaned_phone = '+25' + cleaned_phone[1:]
            elif cleaned_phone.startswith('250'):
                cleaned_phone = '+' + cleaned_phone
            elif not cleaned_phone.startswith('+'):
                cleaned_phone = '+25' + cleaned_phone

            return cleaned_phone
        return phone

    def clean_mtn_phone(self):
        phone = self.cleaned_data.get('mtn_phone')
        if phone:
            # Basic phone validation
            import re
            # Remove any non-digit characters except +
            cleaned_phone = re.sub(r'[^\d+]', '', phone)

            # Check if it's a valid Rwandan phone number format
            if not re.match(r'^(\+?250|0)?[7][0-9]{8}$', cleaned_phone):
                raise forms.ValidationError("Please enter a valid Rwandan phone number (e.g., +250789123456 or 0789123456)")

            # Format to standard format
            if cleaned_phone.startswith('0'):
                cleaned_phone = '+25' + cleaned_phone[1:]
            elif cleaned_phone.startswith('250'):
                cleaned_phone = '+' + cleaned_phone
            elif not cleaned_phone.startswith('+'):
                cleaned_phone = '+25' + cleaned_phone

            return cleaned_phone
        return phone

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        mtn_phone = cleaned_data.get('mtn_phone')

        if payment_method == 'mtn' and not mtn_phone:
            raise forms.ValidationError("MTN phone number is required for MTN Mobile Money payments.")

        return cleaned_data