from django.test import TestCase
from django.contrib.auth import get_user_model
from restaurant.models import MenuCategory, MenuItem, Cart, CartItem, Order, OrderItem, Table, Reservation

User = get_user_model()

class MenuCategoryTest(TestCase):
    def test_str_method(self):
        category = MenuCategory.objects.create(name='Beverages', slug='beverages')
        self.assertEqual(str(category), 'Beverages')

class MenuItemTest(TestCase):
    def setUp(self):
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(
            name='Burger',
            description='Tasty',
            price=10.00,
            stock=10,
            category=self.category,
            low_stock_threshold=5
        )

    def test_available_property(self):
        self.assertTrue(self.item.available)
        self.item.stock = 0
        self.item.save()
        self.assertFalse(self.item.available)

    def test_admin_image_preview_no_image(self):
        self.assertEqual(self.item.admin_image_preview(), '')

class CartTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)

    def test_cart_total(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.item, quantity=2)
        self.assertEqual(cart.total, 30.00)

    def test_cart_item_count(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, item=self.item, quantity=2)
        self.assertEqual(cart.item_count, 1)

class OrderTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)

    def test_order_str(self):
        order = Order.objects.create(user=self.user, total=30.00)
        self.assertIn(f"Order #{order.id}", str(order))

    def test_order_item_subtotal(self):
        order = Order.objects.create(user=self.user, total=30.00)
        order_item = OrderItem.objects.create(order=order, item=self.item, quantity=2, price=15.00)
        self.assertEqual(order_item.subtotal, 30.00)