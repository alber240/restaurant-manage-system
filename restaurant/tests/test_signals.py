from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from restaurant.models import MenuCategory, MenuItem, Order
from restaurant.services import order as order_service
from restaurant.services import cart

User = get_user_model()

class SignalsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)
        cart.add_item_to_cart(self.user, self.item.id, 2)

    def test_order_confirmation_email_sent(self):
        order_obj = order_service.create_order_from_cart(self.user)
        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"Order Confirmation #{order_obj.id}", mail.outbox[0].subject)

    def test_payment_receipt_email_sent(self):
        # Create order first
        order_obj = order_service.create_order_from_cart(self.user)
        order_obj.payment_status = 'completed'
        order_obj.save()
        # The signal for payment receipt should trigger
        self.assertEqual(len(mail.outbox), 2)  # order confirmation + payment receipt
        self.assertIn('Payment Receipt', mail.outbox[1].subject)