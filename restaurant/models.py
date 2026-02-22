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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def item_count(self):
        return self.items.count()

    def __str__(self):
        return f"Cart #{self.id} - {self.user.username}"


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
        ('received', 'Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received', db_index=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.get_status_display()}"


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