"""
This file contains more complex tests for the API.
"""

import unittest
from .test_base import BaseAPITest
import requests
import time
import multiprocessing

class TestStress(BaseAPITest):

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
        self.save_time_to_file(f"Time for single inference job: {T} seconds\n")

        num_concurrent_jobs = 6
        # use multiprocessing to run multiple inference jobs concurrently
        processes = []
        for i in range(num_concurrent_jobs):
            process = multiprocessing.Process(target=self.measure_time_for_single_inference_job)
            processes.append(process)
            process.start()
        start_time = time.time()
        for process in processes:
            process.join()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time for {num_concurrent_jobs} concurrent inference jobs: {elapsed_time} seconds")
        self.save_time_to_file(f"Time for {num_concurrent_jobs} concurrent inference jobs: {elapsed_time} seconds\n")
        self.assertLessEqual(elapsed_time, 1.1 * T)

    def test_stress_2(self):
        self.test_stress()

    def test_stress_3(self):
        self.test_stress()

    def measure_time_for_single_inference_job(self, async_upload=True):
        if async_upload:
            start_time = time.time()
            with open(self.test_image_png, 'rb') as f:
                files = {'image': (self.test_image_png, f, 'image/png')}
                response = requests.post(self.BASE_URL + '/async_upload', files=files)
            # assert it was successful
            self.assertEqual(response.status_code, 202)
            request_id = response.json()['request_id']
            while True:
                response = requests.get(self.BASE_URL + f'/result/{request_id}')
                if response.json()['status'] == 'completed':
                    break
            end_time = time.time()
            elapsed_time = end_time - start_time
            print("It took", elapsed_time, "seconds for the request to complete")
            return elapsed_time

        else:
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

    def save_time_to_file(self, log_message):
        """Helper method to append measured times to a file"""
        with open("measured_times.log", "a") as log_file:
            log_file.write(log_message)

if __name__ == '__main__':
    unittest.main()
