from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import format_html
from model_utils import FieldTracker

User = get_user_model()

class MenuCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='menu_items')
    image = models.ImageField(upload_to='menu_images/', null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=5, help_text="Alert when stock falls below this number")

    class Meta:
        ordering = ['name']

    @property
    def available(self):
        return self.stock > 0

    def get_absolute_url(self):
        return reverse('menu')

    def admin_image_preview(self):
        if self.image:
            return format_html('<img src="{}" height="50"/>', self.image.url)
        return ""

    def __str__(self):
        return f"{self.name} (${self.price})"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)  # ADD THIS LINE
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def item_count(self):
        return self.items.count()

    def __str__(self):
        if self.user:
            return f"Cart #{self.id} - {self.user.username}"
        return f"Cart #{self.id} - Session: {self.session_key}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'item')
        ordering = ['-added_at']

    @property
    def subtotal(self):
        return self.item.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.item.name}"


class Order(models.Model):
    tracker = FieldTracker(fields=['status', 'payment_status'])

    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('card', 'Card'),
        ('mtn', 'MTN Mobile Money'),
        ('airtel', 'Airtel Money'),
        ('cash', 'Cash'),
    ]

    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine In'),
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
    ]

    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Awaiting Assignment'),
        ('assigned', 'Driver Assigned'),
        ('accepted', 'Driver Accepted'),
        ('picked_up', 'Picked Up'),
        ('en_route', 'En Route'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
    ]

    # Core fields
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    
    # Order type
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
    
    # Delivery fields
    delivery_address = models.TextField(blank=True, null=True)
    delivery_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    delivery_phone = models.CharField(max_length=20, blank=True, null=True)
    delivery_instruction = models.TextField(blank=True, null=True, help_text="e.g., Gate code, building number")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    
    # Driver assignment
    driver = models.ForeignKey('Driver', on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    
    # Tip fields
    dine_in_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Rejection reason
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['delivery_status']),
            models.Index(fields=['order_type']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.get_status_display()}"

    def get_delivery_status_display_custom(self):
        return dict(self.DELIVERY_STATUS_CHOICES).get(self.delivery_status, self.delivery_status)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.item.name} (${self.subtotal})"


class Inventory(models.Model):
    item = models.OneToOneField(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    alert_threshold = models.PositiveIntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Inventory'

    def needs_restock(self):
        return self.quantity <= self.alert_threshold

    def __str__(self):
        return f"{self.item.name} - {self.quantity} left"


class Table(models.Model):
    number = models.CharField(max_length=10, unique=True)
    capacity = models.PositiveIntegerField()

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} (seats {self.capacity})"


class Reservation(models.Model):
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, db_index=True)
    email = models.EmailField(blank=True, null=True, help_text="Required for non-logged-in users")
    phone = models.CharField(max_length=20)
    date = models.DateField(db_index=True)
    time = models.TimeField(db_index=True)
    guests = models.PositiveIntegerField()
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['date', 'time']),
        ]

    def __str__(self):
        return f"Reservation #{self.id} - {self.name} ({self.date} at {self.time})"
    
    
# Add to restaurant/models.py - near the top with other imports
from django.contrib.auth.models import AbstractUser
from django.db import models

    
    
# Add this to restaurant/models.py (don't remove anything existing)

# Add this at the end of models.py

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('kitchen', 'Kitchen Staff'),
        ('waiter', 'Waiter/Waitress'),
        ('customer', 'Customer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

# Signals to auto-create profile
from django.db.models.signals import post_save
from django.dispatch import receiver

# Replace the signal handlers at the bottom of models.py with this:

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={'role': 'customer'})

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
        
        
# ==================================================
# RESTAURANT SETTINGS MODEL
# ==================================================

class RestaurantSettings(models.Model):
    """Store all restaurant configuration settings"""
    
    # Delivery Fee Types
    DELIVERY_FEE_CHOICES = (
        ('fixed', 'Fixed Fee'),
        ('distance', 'Distance Based'),
        ('percentage', 'Percentage of Order'),
    )
    
    # Tip Distribution Methods
    TIP_DISTRIBUTION_CHOICES = (
        ('waiter_keeps', 'Waiter Keeps Their Tips'),
        ('pooled', 'Pooled & Shared Among All Staff'),
        ('manager_decides', 'Manager Decides Distribution'),
    )
    
    # Payment Methods
    PAYMENT_METHOD_CHOICES = (
        ('card', 'Credit/Debit Card'),
        ('mobile_money', 'Mobile Money (MTN/Airtel)'),
        ('cash', 'Cash'),
        ('cash_on_delivery', 'Cash on Delivery'),
    )
    
    # ========== General Settings ==========
    restaurant_name = models.CharField(max_length=200, default='Gourmet House')
    restaurant_phone = models.CharField(max_length=20, default='+250 788 123 456')
    restaurant_email = models.EmailField(default='info@gourmethouse.com')
    restaurant_address = models.TextField(default='123 Restaurant Ave, Kigali')
    currency_symbol = models.CharField(max_length=5, default='$')
    currency_code = models.CharField(max_length=10, default='USD')
    
    # ========== Delivery Settings ==========
    enable_delivery = models.BooleanField(default=True, help_text='Enable delivery service')
    delivery_radius_km = models.PositiveIntegerField(default=10, help_text='Maximum delivery distance in kilometers')
    min_order_for_delivery = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Minimum order amount for delivery')
    delivery_fee_type = models.CharField(max_length=20, choices=DELIVERY_FEE_CHOICES, default='fixed')
    delivery_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=3.00, help_text='Fixed delivery fee')
    delivery_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10, help_text='Percentage of order for delivery fee')
    delivery_fee_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=0.50, help_text='Fee per kilometer')
    free_delivery_minimum = models.DecimalField(max_digits=10, decimal_places=2, default=50, help_text='Minimum order for free delivery')
    estimated_delivery_time = models.CharField(max_length=100, default='30-45 minutes')
    
    # ========== Payment Settings ==========
    enable_card_payment = models.BooleanField(default=True)
    enable_mobile_money = models.BooleanField(default=True)
    enable_cash_on_delivery = models.BooleanField(default=True)
    enable_cash_dine_in = models.BooleanField(default=True)
    
    # ========== Tax & Service Settings ==========
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Tax percentage')
    service_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Service charge percentage')
    
    # ========== Tip Settings ==========
    enable_tips = models.BooleanField(default=True)
    tip_distribution_method = models.CharField(max_length=30, choices=TIP_DISTRIBUTION_CHOICES, default='waiter_keeps')
    suggested_tip_percentages = models.JSONField(default=list, help_text='Suggested tip percentages e.g., [10, 15, 18, 20]')
    
    # ========== Business Hours ==========
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='22:00')
    is_open_sunday = models.BooleanField(default=True)
    is_open_monday = models.BooleanField(default=True)
    is_open_tuesday = models.BooleanField(default=True)
    is_open_wednesday = models.BooleanField(default=True)
    is_open_thursday = models.BooleanField(default=True)
    is_open_friday = models.BooleanField(default=True)
    is_open_saturday = models.BooleanField(default=True)
    
    # ========== QR Code Settings ==========
    qr_code_size = models.IntegerField(default=200, help_text='QR code size in pixels')
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Restaurant Setting'
        verbose_name_plural = 'Restaurant Settings'
    
    def __str__(self):
        return f"Settings for {self.restaurant_name}"
    
    def get_delivery_fee(self, order_total=0, distance_km=0):
        """Calculate delivery fee based on settings"""
        if order_total >= self.free_delivery_minimum:
            return 0
        
        if self.delivery_fee_type == 'fixed':
            return self.delivery_fee_amount
        elif self.delivery_fee_type == 'distance':
            return self.delivery_fee_per_km * distance_km
        elif self.delivery_fee_type == 'percentage':
            return order_total * (self.delivery_fee_percentage / 100)
        return 0


# ==================================================
# QR CODE TABLE MODEL
# ==================================================

class QRCodeTable(models.Model):
    """Manage QR codes for restaurant tables"""
    
    table_number = models.CharField(max_length=10, unique=True)
    qr_code_token = models.CharField(max_length=100, unique=True, blank=True)
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['table_number']
    
    def __str__(self):
        return f"Table {self.table_number} QR Code"
    
    def save(self, *args, **kwargs):
        if not self.qr_code_token:
            import uuid
            import hashlib
            # Generate unique token for QR code
            unique_id = f"{self.table_number}_{uuid.uuid4()}"
            self.qr_code_token = hashlib.md5(unique_id.encode()).hexdigest()[:16]
        super().save(*args, **kwargs)
    
    def get_qr_url(self):
        from django.conf import settings
        return f"{settings.SITE_URL}/table/order/{self.qr_code_token}/"


# ==================================================
# DRIVER MODEL
# ==================================================

class Driver(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('busy', 'On Delivery'),
        ('offline', 'Offline'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    phone = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50, choices=[
        ('motorcycle', 'Motorcycle'),
        ('car', 'Car'),
        ('bicycle', 'Bicycle'),
    ], default='motorcycle')
    license_plate = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_deliveries = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Driver: {self.user.username} - {self.vehicle_type}"
    
    def mark_available(self):
        self.is_available = True
        self.status = 'available'
        self.save()
    
    def mark_busy(self):
        self.is_available = False
        self.status = 'busy'
        self.save()


# ==================================================
# DELIVERY ADDRESS MODEL
# ==================================================

class DeliveryAddress(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_addresses')
    address_line = models.TextField()
    house_number = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=50, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.customer.username} - {self.address_line[:50]}"


# ==================================================
# UPDATE ORDER MODEL - Add these fields
# ==================================================

# Add these fields to your existing Order model:
""
order_type = models.CharField(max_length=20, choices=[('dine_in', 'Dine In'), ('pickup', 'Pickup'), ('delivery', 'Delivery')], default='dine_in')
table = models.ForeignKey('Table', on_delete=models.SET_NULL, null=True, blank=True)
delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.SET_NULL, null=True, blank=True)
driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
dine_in_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
delivery_tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)
estimated_delivery_time = models.DateTimeField(null=True, blank=True)



class DeliveryAddress(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_addresses')
    address_line = models.TextField()
    house_number = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=50, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.customer.username} - {self.address_line[:50]}"