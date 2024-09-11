"""
This module contains tests for the GET /result endpoint, but
only for the part of it that is independent of the functionality of the POST /async_upload endpoint.
"""


import unittest
from .test_base import BaseAPITest
import requests


class TestGetResult(BaseAPITest):
    """Endpoint: GET /result/<request_id>"""
    def setUp(self):
        super().setUp()
        self.partial_endpoint = self.BASE_URL + '/result/'
    def test_returns_404_if_id_not_found(self):
        non_existent_ids = ['non_existent_id', 'hi ', '  ', '999', 9999, 1000001, 'משהו בעברית']
        # 999 and 1000001 must not be in the database because they are outside the range [10000, 1000000]

        for request_id in non_existent_ids:
            with self.subTest(request_id=request_id):
                response = requests.get(self.partial_endpoint + str(request_id))
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {'error': {'code': 404, 'message': 'ID not found'}})



if __name__ == '__main__':
    unittest.main()
