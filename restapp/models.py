#restapp/models.py


from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('server', 'Server'),
        ('chef', 'Chef'),
        ('cashier', 'Cashier'),
        ('customer', 'Customer'),
        ('deliveryboy', 'Delivery Boy'),  # Add this role
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'  # This sets the default role
    )
    phone = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return self.username

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    hire_date = models.DateField(auto_now_add=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shift = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ("can_manage_menu", "Can manage menu items"),
            ("can_manage_orders", "Can manage orders"),
            ("can_manage_staff", "Can manage staff"),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.get_role_display()}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Reservation(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    table = models.ForeignKey('Table', on_delete=models.CASCADE)
    reservation_time = models.DateTimeField()
    party_size = models.PositiveIntegerField()
    special_requests = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
        ('completed', 'Completed'),
    ], default='confirmed')
    
    class Meta:
        ordering = ['reservation_time']

    def delete(self, *args, **kwargs):
        # Mark table as available before deletion
        self.table.is_occupied = False
        self.table.save()
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"Reservation #{self.id} for {self.customer.username}"

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True)
    
    def __str__(self):
        return self.name

class Table(models.Model):
    number = models.IntegerField(unique=True)
    capacity = models.IntegerField()
    is_occupied = models.BooleanField(default=False)

    def get_active_orders_count(self):
        return self.order_set.filter(status__in=['pending', 'preparing']).count()
    
    def __str__(self):
        return f"Table {self.number}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('paid', 'Paid'),
    ]

    @property
    def status_index(self):
        return [s[0] for s in self.STATUS_CHOICES].index(self.status)
    
    
    def total(self):
        return sum(item.menu_item.price * item.quantity for item in self.items.all())

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True)
    order_type = models.CharField(max_length=10, choices=[('pickup', 'Pickup'), ('delivery', 'Delivery')], null=True)
    
    estimated_time = models.PositiveIntegerField(null=True, blank=True)
    
    table = models.ForeignKey(Table, on_delete=models.CASCADE, null=True)
    server = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders_served',
        null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    _total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Add this field

    delivery_boy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='delivery_orders'
    )

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.10, null=True)  # Example: 10% tax

    def subtotal(self):
        return sum(item.quantity * item.menu_item.price for item in self.orderitem_set.all())

    def tax(self):
        return self.subtotal() * self.tax_rate

    def total(self):
        return self.subtotal() + self.tax()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - Table {self.table.number}"
    
   

class Rating(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='ratings')
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['order', 'customer']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} stars for Order #{self.order.id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_requests = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} for Order #{self.order.id}"
    
    def subtotal(self):
        return self.menu_item.price * self.quantity


class DeliveryAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_address', null=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"Delivery address for Order #{self.order.id}"

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20)  # e.g., kg, liters, pieces
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        ordering = ['name']

class Stock(models.Model):
    ingredient = models.OneToOneField(Ingredient, on_delete=models.CASCADE, related_name='stock')
    current_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    alert_threshold = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Stock: {self.ingredient.name}"

    @property
    def is_low(self):
        return self.current_quantity <= self.alert_threshold

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjust', 'Adjustment'),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference_number = models.CharField(max_length=50, blank=True)  # For purchase orders or other references
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.ingredient.name} ({self.quantity} {self.ingredient.unit})"

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Update stock quantity based on transaction type
        stock, created = Stock.objects.get_or_create(ingredient=self.ingredient)
        
        if self.transaction_type == 'in':
            stock.current_quantity += self.quantity
        elif self.transaction_type == 'out':
            stock.current_quantity -= self.quantity
        elif self.transaction_type == 'adjust':
            stock.current_quantity = self.quantity
            
        stock.save()
        super().save(*args, **kwargs)

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('stock_adjust', 'Stock Adjusted'),
        ('order_status', 'Order Status Changed'),
        ('table_status', 'Table Status Changed'),
        ('staff_status', 'Staff Status Changed'),
        ('Deliverd', 'Order Deliverd'),
        ('accepted', 'Order Accepted'),

    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    related_order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)

    related_model = models.CharField(max_length=50, blank=True)  # e.g., 'Order', 'Ingredient', 'Table'
    related_id = models.IntegerField(null=True, blank=True)  # ID of the related object
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.user.username} {self.get_action_type_display()} - {self.description}"