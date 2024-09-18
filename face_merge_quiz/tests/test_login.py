import unittest
from app import app

class TestLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app  # Create the app
        cls.client = cls.app.test_client()  # Create a test client
        cls.app.testing = True

    def setUp(self):
        # Push an application context
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Pop the application context
        self.app_context.pop()

    def _login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def test_get_login(self):
        response = self.client.get('/login')
        self.assertIn(b'Login', response.data)
        self.assertIn(b'Username', response.data)
        self.assertIn(b'Password', response.data)
        self.assertIn(b'Sign up here', response.data)

    def test_login_unsigned_up_user(self):
        response = self._login('notLoggedInUser', 'notLoggedInPassword')
        self.assertIn(b'Login unsuccessful. Please check username and password', response.data)

if __name__ == '__main__':
    unittest.main()



    # import requests
    #
    # # URL of the login form
    # url = "http://localhost:5001/login"  # Replace with your actual URL
    #
    # # Data to be submitted
    # form_data = {
    #     'username': 'testuser',  # Replace with actual username
    #     'password': 'testpassword'  # Replace with actual password
    # }
    #
    # # Send POST request with form data
    # response = requests.post(url, data=form_data)
    #
    # # Check the response
    # if response.status_code == 200:
    #     print("Login request successful!")
    #     print("Response text:", response.text)
    # else:
    #     print(f"Failed to login, status code: {response.status_code}")

