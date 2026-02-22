from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class APITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='api_user', password='12345', email='api@example.com')
        self.staff_user = User.objects.create_user(username='api_staff', password='12345', is_staff=True)

    def test_obtain_token(self):
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_user',
            'password': '12345'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_protected_endpoint_requires_token(self):
        response = self.client.get(reverse('protected-endpoint'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_token(self):
        token_response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_user',
            'password': '12345'
        })
        token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('protected-endpoint'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], 'api_user')

    def test_staff_only_endpoint_requires_staff(self):
        # user token
        token_response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_user',
            'password': '12345'
        })
        token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('api_staff_dashboard'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # staff token
        token_response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_staff',
            'password': '12345'
        })
        token = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('api_staff_dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)