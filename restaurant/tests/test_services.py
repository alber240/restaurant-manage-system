from django.test import TestCase
from django.contrib.auth import get_user_model
from restaurant.models import MenuCategory, MenuItem, Cart, Table
from restaurant.services import cart, order, inventory, reservation

User = get_user_model()

class CartServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)

    def test_add_item_to_cart(self):
        cart.add_item_to_cart(self.user, self.item.id, 2)
        cart_obj = cart.get_cart(self.user)
        self.assertEqual(cart_obj.items.count(), 1)
        self.assertEqual(cart_obj.items.first().quantity, 2)

    def test_remove_item_from_cart(self):
        cart.add_item_to_cart(self.user, self.item.id, 2)
        cart.remove_item_from_cart(self.user, self.item.id)
        cart_obj = cart.get_cart(self.user)
        self.assertEqual(cart_obj.items.count(), 0)

    def test_update_cart_item_quantity(self):
        cart.add_item_to_cart(self.user, self.item.id, 2)
        cart.update_cart_item_quantity(self.user, self.item.id, 5)
        cart_obj = cart.get_cart(self.user)
        self.assertEqual(cart_obj.items.first().quantity, 5)

    def test_clear_cart(self):
        cart.add_item_to_cart(self.user, self.item.id, 2)
        cart.clear_cart(self.user)
        cart_obj = cart.get_cart(self.user)
        self.assertEqual(cart_obj.items.count(), 0)

class OrderServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)
        cart.add_item_to_cart(self.user, self.item.id, 2)

    def test_create_order_from_cart(self):
        order_obj = order.create_order_from_cart(self.user)
        self.assertEqual(order_obj.user, self.user)
        self.assertEqual(order_obj.total, 30.00)
        self.assertEqual(order_obj.items.count(), 1)
        # Cart should be cleared
        cart_obj = cart.get_cart(self.user)
        self.assertEqual(cart_obj.items.count(), 0)

    def test_create_order_empty_cart_raises_error(self):
        cart.clear_cart(self.user)
        with self.assertRaises(ValueError):
            order.create_order_from_cart(self.user)

class InventoryServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, low_stock_threshold=2, category=self.category)

    def test_deduct_stock_success(self):
        inventory.deduct_stock(self.item.id, 3)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock, 2)

    def test_deduct_stock_insufficient_raises_error(self):
        with self.assertRaises(ValueError) as context:
            inventory.deduct_stock(self.item.id, 10)
        self.assertIn('Insufficient stock', str(context.exception))

    def test_check_low_stock(self):
        self.item.stock = 2
        self.item.save()
        self.assertTrue(inventory.check_low_stock(self.item))
        self.item.stock = 5
        self.item.save()
        self.assertFalse(inventory.check_low_stock(self.item))

class ReservationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        self.table = Table.objects.create(number='1', capacity=4)

    def test_create_reservation_authenticated(self):
        data = {
            'name': 'John Doe',
            #'email': 'john@example.com',
            'phone': '0788888888',
            'date': '2026-03-01',
            'time': '19:00',
            'guests': 2,
            'table': self.table,
            'special_requests': ''
        }
        res = reservation.create_reservation(data, user=self.user)
        self.assertEqual(res.customer, self.user)
        self.assertEqual(res.email, self.user.email)  # should use user's email if not provided