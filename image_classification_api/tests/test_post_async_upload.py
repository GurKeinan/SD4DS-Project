"""
This module contains tests for the POST /async_upload endpoint, but
only for the part of it that is independent of the functionality of the GET /result endpoint.
"""



import unittest
import time
from .test_base import BaseAPITest
import requests


class TestPostAsyncUpload(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.endpoint = self.BASE_URL + '/async_upload'

    def test_content_type_is_json(self):
        with open(self.test_image_png, 'rb') as f:
            files = {'image': ('britney.png', f, 'image/png')}
            response = requests.post(self.endpoint, files=files)
        self.assertEqual(response.headers['Content-Type'], 'application/json')


    def test_it_returns_202_when_image_is_uploaded(self):
        time.sleep(1)
        test_files = [(self.test_image_jpeg, 'image/jpeg'), (self.test_image_png, 'image/png')]
        for file, MIME_type in test_files:
            with self.subTest(file=file):
                with open(file, 'rb') as f:
                    files = {'image': (file, f, MIME_type)}
                    response = requests.post(self.endpoint, files=files)
                self.assertEqual(response.status_code, 202)

    def test_request_id_is_returned_and_in_correct_format(self):
        time.sleep(1)
        with open(self.test_image_png, 'rb') as f:
            files = {'image': ('britney.png', f, 'image/png')}
            response = requests.post(self.endpoint, files=files)
        self.assertEqual(response.status_code, 202)
        self.assertIn('request_id', response.json())
        request_id = response.json()['request_id']
        self.assertIsInstance(request_id, int)
        # assert it is in [10000, 1000000]:
        self.assertGreaterEqual(int(request_id), 10000)
        self.assertLessEqual(int(request_id), 1000000)

    def test_uniqueness_of_request_id(self):
        time.sleep(1)
        with open(self.test_image_png, 'rb') as f:
            files = {'image': ('britney.png', f, 'image/png')}
            response = requests.post(self.endpoint, files=files)
        self.assertEqual(response.status_code, 202)
        request_id1 = response.json()['request_id']
        with open(self.test_image_jpeg, 'rb') as f:
            files = {'image': ('test_img.jpeg', f, 'image/jpeg')}
            response = requests.post(self.endpoint, files=files)
        self.assertEqual(response.status_code, 202)
        request_id2 = response.json()['request_id']
        self.assertNotEqual(request_id1, request_id2)

    def test_it_returns_400_when_no_file_is_uploaded(self):
        time.sleep(1)
        response = requests.post(self.endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': {'code': 400, 'message': 'No file part'}})


if __name__ == '__main__':
    unittest.main()
