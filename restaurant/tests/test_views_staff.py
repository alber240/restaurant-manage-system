from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from restaurant.models import MenuCategory, MenuItem, Order

User = get_user_model()

class StaffViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username='staff', password='12345', is_staff=True)
        self.normal_user = User.objects.create_user(username='normal', password='12345')
        self.category = MenuCategory.objects.create(name='Food', slug='food')
        self.item = MenuItem.objects.create(name='Pizza', price=15.00, stock=5, category=self.category)

    def test_kitchen_dashboard_requires_staff(self):
        self.client.login(username='normal', password='12345')
        response = self.client.get(reverse('kitchen'))
        self.assertEqual(response.status_code, 302)  # redirect

    def test_kitchen_dashboard_staff(self):
        self.client.login(username='staff', password='12345')
        response = self.client.get(reverse('kitchen'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'restaurant/kitchen/orders.html')

    def test_inventory_dashboard_staff(self):
        self.client.login(username='staff', password='12345')
        response = self.client.get(reverse('inventory_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pizza')