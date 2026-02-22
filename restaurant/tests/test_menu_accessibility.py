import unittest

from django.test import TestCase
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

@unittest.skip("Skipping accessibility tests – chromedriver not configured")
class MenuAccessibilityTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=cls.service)
        super().setUpClass()

    def test_menu_page_elements(self):
        self.driver.get("http://localhost:8000/menu/")
        heading = self.driver.find_element(By.TAG_NAME, "h1")
        self.assertIsNotNone(heading)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()