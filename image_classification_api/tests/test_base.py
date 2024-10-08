import unittest
import socket
import time

class BaseAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        time.sleep(1)  # because gemini API has a rate limit
        cls.test_image_png = 'tests/assets/britney.png'
        cls.test_image_jpeg = 'tests/assets/test_img.jpeg'

        port = 6000  # should equal to the port before the : in the docker-compose file
        cls.BASE_URL = f"http://localhost:{port}"

        # NEW FROM SEPTEMBER 12TH: Instead of starting the app from here, first run docker-compose up and then run the tests
        # (run the tests in your laptop, not in the container)

        # # Check if the server is already running on the specified port
        # if not cls.is_server_running(port):
        #     def run_flask():
        #         app.app.run(host='0.0.0.0', port=port)
        #
        #     threading.Thread(target=run_flask, daemon=True).start()
        # else:
        #     print(f"Server is already running on port {port} :)")

    @staticmethod
    def is_server_running(port):
        """Check if the server is running by trying to connect to the port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0


if __name__ == '__main__':
    unittest.main()
