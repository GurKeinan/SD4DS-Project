import unittest
from app import app

class TestLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app  # Create the app
        cls.client = cls.app.test_client()  # Create a test client

    def setUp(self):
        # Push an application context
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Pop the application context
        self.app_context.pop()

    def test_homepage(self):
        """Test the homepage route."""
        response = self.client.get('/')  # Directly calling the homepage URL
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome', response.data)  # Check if 'Welcome' is in the HTML

    def test_face_merge_route(self):
        """Test the face merge route."""
        response = self.client.get('/face_merge')  # Directly calling the face merge URL
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Face Merge', response.data)

if __name__ == '__main__':
    unittest.main()
