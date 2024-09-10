import unittest
from .test_base import BaseAPITest
import requests


class MyTestCase(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.endpoint = self.BASE_URL + '/async_upload'
        self.test_image_png = 'tests/assets/britney.png'
        self.test_image_jpeg = 'tests/assets/test_img.jpeg'
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
