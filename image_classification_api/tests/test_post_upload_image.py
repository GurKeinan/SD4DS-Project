import unittest
from .test_base import BaseAPITest
import requests

class TestPostUploadImage(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.endpoint = self.BASE_URL + '/upload_image'


    def test_it_returns_200_when_image_is_uploaded(self):
        test_files = [(self.test_image_jpeg, 'image/jpeg'), (self.test_image_png, 'image/png')]
        for file, MIME_type in test_files:
            with self.subTest(file=file):
                with open(file, 'rb') as f:
                    files = {'image': (file, f, MIME_type)}
                    response = requests.post(self.endpoint, files=files)
                self.assertEqual(response.status_code, 200)

    def _test_successful_upload(self, true_filename='britney.png'):
        filenames = ["test_image.png", "somepic.png", "image with spaces.png", "image_with_ünîçødé.png"]

        for filename in filenames:
            with self.subTest(filename=filename):
                with open(true_filename, 'rb') as image_file:
                    files = {'image': (filename, image_file, 'image/png')}
                    response = requests.post(self.endpoint, files=files)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['Content-Type'], 'application/json')

                data = response.json()
                self.assertIn('matches', data)
                self.assertIsInstance(data['matches'], list)
                for match in data['matches']:
                    self.assertIn('name', match)
                    self.assertIn('score', match)
                    self.assertIsInstance(match['name'], str)
                    self.assertIsInstance(match['score'], float)
                    self.assertGreater(match['score'], 0.0)
                    self.assertLessEqual(match['score'], 1.0)

    def test_successful_uploads(self):
        for true_file_path in [self.test_image_png, self.test_image_jpeg]:
            with self.subTest(true_file_path=true_file_path):
                self._test_successful_upload(true_file_path)


    def test_it_returns_400_when_no_file_is_uploaded(self):
        response = requests.post(self.endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': {'code': 400, 'message': 'No file part'}})




if __name__ == '__main__':
    unittest.main()