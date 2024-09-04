import unittest
import requests
import time
import threading
import app


class TestStatusEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        port = 5000
        cls.BASE_URL = f"http://localhost:{port}"
        print('hiiiiiiiiiiiiii before app.app.run')
        def run_flask():
            app.app.run(host='0.0.0.0', port=port)

        threading.Thread(target=run_flask, daemon=True).start()
        # Daemon threads automatically shut down when the main process exits.
        print('hiiiiiiiiiiiiii after app.app.run')

    def test_status_endpoint(self):
        response = requests.get(f"{self.BASE_URL}/status")

        # Check if the response status code is 200
        self.assertEqual(response.status_code, 200)

        # Check if the response is in JSON format
        self.assertEqual(response.headers['Content-Type'], 'application/json')

        # Parse the JSON response
        data = response.json()

        # Check if the response has the correct structure
        self.assertIn('status', data)
        status = data['status']

        # Check if all required fields are present
        required_fields = ['uptime', 'processed', 'health', 'api_version']
        for field in required_fields:
            self.assertIn(field, status)

        # Check if 'processed' has all required subfields
        processed_fields = ['success', 'fail', 'running', 'queued']
        for field in processed_fields:
            self.assertIn(field, status['processed'])

        # Check data types and value ranges
        self.assertIsInstance(status['uptime'], (int, float))
        self.assertGreaterEqual(status['uptime'], 0)

        self.assertIsInstance(status['processed']['success'], int)
        self.assertIsInstance(status['processed']['fail'], int)
        self.assertIsInstance(status['processed']['running'], int)
        self.assertIsInstance(status['processed']['queued'], int)

        self.assertIn(status['health'], ['ok', 'error'])

        self.assertIsInstance(status['api_version'], int)
        self.assertEqual(status['api_version'], 2)  # Current API version is 2

    def test_uptime_increases(self):
        # Make two requests with a small delay to check if uptime increases
        response1 = requests.get(f"{self.BASE_URL}/status")
        time.sleep(1)
        response2 = requests.get(f"{self.BASE_URL}/status")

        uptime1 = response1.json()['status']['uptime']
        uptime2 = response2.json()['status']['uptime']

        self.assertGreater(uptime2, uptime1)


if __name__ == '__main__':
    unittest.main()