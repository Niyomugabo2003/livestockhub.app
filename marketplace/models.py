from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_parent(self):
        return self.parent is None

    @property
    def has_subcategories(self):
        return self.subcategories.exists()

    def get_all_subcategories(self):
        """Get all subcategories recursively"""
        subcategories = []
        for subcategory in self.subcategories.filter(is_active=True):
            subcategories.append(subcategory)
            subcategories.extend(subcategory.get_all_subcategories())
        return subcategories


class Product(models.Model):
    LIVESTOCK_TYPES = (
        ('cattle', 'Cattle'),
        ('goats', 'Goats'),
        ('sheep', 'Sheep'),
        ('poultry', 'Poultry'),
        ('pigs', 'Pigs'),
        ('rabbits', 'Rabbits'),
        ('fish', 'Fish'),
        ('others', 'Others'),
    )
    
    # New product types based on livestock type
    CATTLE_TYPES = (
        ('cow', 'Cow'),
        ('bull', 'Bull'),
        ('calf', 'Calf'),
        ('heifer', 'Heifer'),
        ('ox', 'Ox'),
    )
    
    GOAT_TYPES = (
        ('meat', 'Meat Goat'),
        ('milk', 'Dairy Goat'),
        ('kid', 'Kid'),
        ('buck', 'Buck'),
        ('doe', 'Doe'),
    )
    
    SHEEP_TYPES = (
        ('lamb', 'Lamb'),
        ('mutton', 'Mutton'),
        ('ram', 'Ram'),
        ('ewe', 'Ewe'),
        ('lamb_meat', 'Lamb Meat'),
    )
    
    POULTRY_TYPES = (
        ('meat', 'Meat Chicken'),
        ('eggs', 'Layer Chicken'),
        ('broiler', 'Broiler'),
        ('rooster', 'Rooster'),
        ('hen', 'Hen'),
        ('chick', 'Chick'),
    )
    
    PIG_TYPES = (
        ('pork', 'Pork'),
        ('bacon', 'Bacon'),
        ('sow', 'Sow'),
        ('boar', 'Boar'),
        ('piglet', 'Piglet'),
    )
    
    RABBIT_TYPES = (
        ('meat', 'Rabbit Meat'),
        ('doe_rabbit', 'Doe Rabbit'),
        ('buck_rabbit', 'Buck Rabbit'),
        ('fryer', 'Fryer'),
    )
    
    FISH_TYPES = (
        ('tilapia', 'Tilapia'),
        ('catfish', 'Catfish'),
        ('trout', 'Trout'),
        ('salmon', 'Salmon'),
        ('freshwater', 'Freshwater Fish'),
        ('saltwater', 'Saltwater Fish'),
    )
    
    OTHER_TYPES = (
        ('bees', 'Bees/Honey'),
        ('snails', 'Snails'),
        ('guinea_fowl', 'Guinea Fowl'),
        ('turkey', 'Turkey'),
        ('duck', 'Duck'),
    )

    seller = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'seller'})
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock_quantity = models.IntegerField(validators=[MinValueValidator(0)])
    livestock_type = models.CharField(max_length=20, choices=LIVESTOCK_TYPES)
    
    # New field for specific animal types
    animal_type = models.CharField(max_length=20, blank=True, null=True)
    
    image = models.ImageField(upload_to='products/')
    image2 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Additional Image 1')
    image3 = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Additional Image 2')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_animal_type_choices(self):
        """Return the appropriate choices based on livestock_type"""
        type_mapping = {
            'cattle': self.CATTLE_TYPES,
            'goats': self.GOAT_TYPES,
            'sheep': self.SHEEP_TYPES,
            'poultry': self.POULTRY_TYPES,
            'pigs': self.PIG_TYPES,
            'rabbits': self.RABBIT_TYPES,
            'fish': self.FISH_TYPES,
            'others': self.OTHER_TYPES,
        }
        return type_mapping.get(self.livestock_type, [])

    def get_animal_type_display(self):
        """Get display name for animal_type"""
        if not self.animal_type:
            return ""
        
        type_mapping = {
            'cattle': dict(self.CATTLE_TYPES),
            'goats': dict(self.GOAT_TYPES),
            'sheep': dict(self.SHEEP_TYPES),
            'poultry': dict(self.POULTRY_TYPES),
            'pigs': dict(self.PIG_TYPES),
            'rabbits': dict(self.RABBIT_TYPES),
            'fish': dict(self.FISH_TYPES),
            'others': dict(self.OTHER_TYPES),
        }
        
        choices = type_mapping.get(self.livestock_type, {})
        return choices.get(self.animal_type, self.animal_type)

    def reduce_stock(self, quantity):
        if self.stock_quantity >= quantity:
            self.stock_quantity -= quantity
            self.save()
            return True
        return False

    def get_images(self):
        """Return all images for the product"""
        images = []
        if self.image:
            images.append(self.image)
        if self.image2:
            images.append(self.image2)
        if self.image3:
            images.append(self.image3)
        return images

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.quantity * self.product.price

class Report(models.Model):
    REPORT_TYPES = (
        ('sales', 'Sales Report'),
        ('products', 'Products Report'),
        ('orders', 'Orders Report'),
        ('revenue', 'Revenue Report'),
        ('users', 'Users Report'),
        ('inventory', 'Inventory Report'),
    )
    
    REPORT_PERIODS = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Date Range'),
    )

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    period = models.CharField(max_length=20, choices=REPORT_PERIODS)
    start_date = models.DateField()
    end_date = models.DateField()
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()  # Store report data
    
    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.start_date} to {self.end_date}"