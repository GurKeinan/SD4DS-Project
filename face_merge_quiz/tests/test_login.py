import unittest
from app import app
from flask import url_for

class TestLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app  # Create the app
        cls.client = cls.app.test_client()  # Create a test client

    def test_homepage(self):
        """Test the homepage route."""
        response = self.client.get(url_for('home'))  # Assuming you have a route named 'home'
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data)  # Check if 'Welcome' is in the HTML

    def test_face_merge_route(self):
        """Test the face merge route."""
        response = self.client.get(url_for('face_merge'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Face Merge', response.data)

if __name__ == '__main__':
    unittest.main()
