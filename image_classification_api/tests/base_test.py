import unittest
import threading
import app  # works if CMD ["python", "-m", "tests.get_status"]
# or if running python -m unittest discover
# or if running python -m unittest discover <name of directory with tests>

class BaseAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        port = 5000
        cls.BASE_URL = f"http://localhost:{port}"

        def run_flask():
            app.app.run(host='0.0.0.0', port=port)

        threading.Thread(target=run_flask, daemon=True).start()
        # Daemon threads automatically shut down when the main process exits.


if __name__ == '__main__':
    unittest.main()
