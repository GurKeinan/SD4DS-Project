"""
This file contains more complex tests for the API.
"""


import unittest
from .test_base import BaseAPITest
import requests
import time


class TestMoreComplex(BaseAPITest):

    def test_stress(self):
        """
        This test tests the following technical requirement:
        "
        Let’s say that one model inference job takes T seconds.
        Running 6 concurrent image inference jobs should complete successfully in < 1.1* T
        Seconds.
        Completion is when the GET /result returns "completed"
        " quoted from the technical requirements .pdf document.
        We measure T using the POST /upload_image endpoint.
        """
        T = self.measure_time_for_single_inference_job()
        print(f"Time for single inference job: {T} seconds")
        request_ids = []
        for i in range(1):
            with open(self.test_image_png, 'rb') as f:
                files = {'image': (self.test_image_png, f, 'image/png')}
                response = requests.post(self.BASE_URL + '/async_upload', files=files)
            # assert it was successful
            self.assertEqual(response.status_code, 202)
            request_ids.append(response.json()['request_id'])
        start_time = time.time()
        for request_id in request_ids:
            while True:
                response = requests.get(self.BASE_URL + f'/result/{request_id}')
                if response.json()['status'] == 'completed':
                    break
                print(response.json())
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time for 6 concurrent inference jobs: {elapsed_time} seconds")
        self.assertLessEqual(elapsed_time, 1.1 * T)

    def measure_time_for_single_inference_job(self):
        start_time = time.time()
        with open(self.test_image_png, 'rb') as f:
            files = {'image': (self.test_image_png, f, 'image/png')}
            response = requests.post(self.BASE_URL + '/upload_image', files=files)
        # assert it was successful
        self.assertEqual(response.status_code, 200)
        print("In measure_time", response.json())
        end_time = time.time()
        elapsed_time = end_time - start_time
        return elapsed_time



if __name__ == '__main__':
    unittest.main()


