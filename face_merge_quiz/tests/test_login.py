import unittest
from app import app, mongo


class TestLogin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app  # Create the app
        cls.client = cls.app.test_client()  # Create a test client
        cls.app.testing = True
        print('setUpClass TestLogin')

    def setUp(self):
        # Push an application context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Clear the users collection before each test
        with self.app.app_context():
            mongo.db.users.delete_many({})

    def tearDown(self):
        # Pop the application context
        self.app_context.pop()
        print('tearDown TestLogin')

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

    def _signup(self, username, password):
        return self.client.post('/sign-up', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def test_get_signup(self):
        response = self.client.get('/sign-up')
        self.assertIn(b'Sign Up', response.data)
        self.assertIn(b'Username', response.data)
        self.assertIn(b'Password', response.data)
        self.assertIn(b'Already have an account?', response.data)

    def test_post_signup(self):
        response = self._signup('testuser', 'testpassword')
        self.assertIn(b'Account created successfully!', response.data)
        self.assertIn(b'Join a Game', response.data)

    def test_post_signup_existing_user(self):
        self._signup('testuser2', 'testpassword')
        response = self._signup('testuser2', 'testpassword')
        self.assertIn(b'Username already exists. Please choose another one.', response.data)

    def test_login_signed_up_user(self):
        # First sign up the user
        self._signup('testuser3', 'testpassword')

        # Then try to log in with the same credentials
        response = self._login('testuser3', 'testpassword')

        # Check if the login was successful (you might need to adjust the success message)
        self.assertIn(b'Logged in successfully!', response.data)
        self.assertIn(b'Welcome', response.data)


if __name__ == '__main__':
    unittest.main()