"""
This file is for testing that the combination of the POST /async_upload and GET /result endpoints work as expected.
"""

import unittest
from .test_base import BaseAPITest
import requests
import time

ENOUGH_TIME_FOR_PROCESSING = 5  # seconds

class TestPostAsyncUpload(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.async_upload_endpoint = self.BASE_URL + '/async_upload'
        self.result_partial_endpoint = self.BASE_URL + '/result/'
        # full endpoint is self.result_partial_endpoint + str(request_id)

    def test_get_result_returns_200_if_request_id_exists(self):
        time.sleep(1)
        with open(self.test_image_png, 'rb') as f:
            response = requests.post(self.async_upload_endpoint, files={'image': (self.test_image_png, f, 'image/png')})
        self.assertEqual(response.status_code, 202)
        request_id = response.json()['request_id']
        response = requests.get(self.result_partial_endpoint + str(request_id))
        self.assertEqual(response.status_code, 200)

    def test_behavior_of_get_status_when_status_is_completed(self):
        time.sleep(1)
        with open(self.test_image_png, 'rb') as f:
            response = requests.post(self.async_upload_endpoint, files={'image': (self.test_image_png, f, 'image/png')})
        self.assertEqual(response.status_code, 202)
        request_id = response.json()['request_id']
        time.sleep(ENOUGH_TIME_FOR_PROCESSING) # this should be sufficient to ensure the status should be completed

        response = requests.get(self.result_partial_endpoint + str(request_id))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(data['status'], 'completed')
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