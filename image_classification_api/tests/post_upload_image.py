import unittest
from .base_test import BaseAPITest
import requests

class TestUploadImage(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.endpoint = self.BASE_URL + '/upload_image'
        self.test_image_png = 'tests/assets/britney.png'
        self.test_image_jpeg = 'tests/assets/test_img.jpeg'

    def test_it_returns_200_when_image_is_uploaded(self):
        test_files = [(self.test_image_jpeg, 'image/jpeg'), (self.test_image_png, 'image/png')]
        for file, MIME_type in test_files:
            with self.subTest(file=file):
                with open(file, 'rb') as f:
                    files = {'image': (file, f, MIME_type)}
                    response = requests.post(self.endpoint, files=files)
                    print(response.json())
                self.assertEqual(response.status_code, 200)

    def test_successful_upload_png(self):
        filenames = ["test_image.png", "somepic.png", "image with spaces.png", "image_with_ünîçødé.png"]

        for filename in filenames:
            with self.subTest(filename=filename):
                with open(self.test_image_png, 'rb') as image_file:
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


if __name__ == '__main__':
    unittest.main()