from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SellerProfile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your address'}),
        required=False
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your city'})
    )
    
    # Remove 'admin' from choices for registration form
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('seller', 'Seller'),
    ]
    
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='customer'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'user_type', 
                 'phone_number', 'address', 'city']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
        
        # Make email required
        self.fields['email'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.user_type = self.cleaned_data['user_type']  # ADD THIS LINE - Save the user_type
        if commit:
            user.save()
            # If user registered as seller, create seller profile
            if user.user_type == 'seller':
                SellerProfile.objects.create(user=user, business_name=f"{user.username}'s Business")
        return user

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'address', 'city']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Username',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'address': 'Address',
            'city': 'City',
        }

class SellerProfileForm(forms.ModelForm):
    class Meta:
        model = SellerProfile
        fields = ['business_name', 'business_registration', 'description']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter business name'}),
            'business_registration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business registration number (optional)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your business'}),
        }
        labels = {
            'business_name': 'Business Name',
            'business_registration': 'Registration Number',
            'description': 'Business Description',
        }

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

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )