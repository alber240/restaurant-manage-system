from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from restaurant.models import MenuCategory, MenuItem, Cart

User = get_user_model()

class CustomerViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'restaurant/home.html')

    def test_menu_view(self):
        response = self.client.get(reverse('menu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pizza')

    def test_add_to_cart_requires_login(self):
        response = self.client.post(reverse('add_to_cart', args=[self.item.id]), {'quantity': 2})
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_add_to_cart_authenticated(self):
        self.client.login(username='testuser', password='12345')
        response = self.client.post(reverse('add_to_cart', args=[self.item.id]), {'quantity': 2})
        self.assertEqual(response.status_code, 302)  # redirect to menu
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)

    def test_view_cart_authenticated(self):
         self.client.login(username='testuser', password='12345')
    # Add an item to cart to create it
         self.client.post(reverse('add_to_cart', args=[self.item.id]), {'quantity': 1})
         response = self.client.get(reverse('view_cart'))
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'restaurant/customer/cart.html')