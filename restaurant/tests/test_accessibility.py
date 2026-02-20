from django.test import TestCase, Client
from django.urls import reverse
from axe_selenium_python import Axe
from selenium import webdriver
import unittest

class AccessibilityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client()
        cls.driver = webdriver.Chrome()  # Requires chromedriver
        
    def test_cart_page_accessibility(self):
        # Login first if required
        self.client.login(username='admin', password='password')
        
        # Get the page
        url = reverse('view_cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Test with axe
        self.driver.get(f"http://localhost:8000{url}")
        axe = Axe(self.driver)
        axe.inject()
        results = axe.run()
        self.assertEqual(len(results["violations"]), 0, 
                        msg=f"Accessibility violations found: {results['violations']}")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

if __name__ == '__main__':
    unittest.main()