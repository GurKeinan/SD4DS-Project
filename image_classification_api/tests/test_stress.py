import unittest
import requests
import time
import threading
from .test_base import BaseAPITest

def measure_time_for_single_inference_job(base_url, valid_image_file):
    start_time = time.time()
    with open(valid_image_file, 'rb') as f:
        files = {'image': (valid_image_file, f, 'image/png')}
        response = requests.post(base_url + '/async_upload', files=files)
    assert response.status_code == 202
    request_id = response.json()['request_id']
    while True:
        response = requests.get(base_url + f'/result/{request_id}')
        if response.json()['status'] == 'completed':
            break
    end_time = time.time()
    elapsed_time = end_time - start_time
    return elapsed_time

class StressTest(BaseAPITest):

    def test_stress(self):
        """
        This test tests the following technical requirement:
        Run 6 concurrent image inference jobs and check they finish in less than 1.1 * T.
        """
        T = self.measure_time_for_single_inference_job()
        self.save_time_to_file(f"Time for single inference job: {T} seconds\n")

        num_concurrent_jobs = 6
        threads = []
        start_time = time.time()

        # Start concurrent threads
        for _ in range(num_concurrent_jobs):
            thread = threading.Thread(target=measure_time_for_single_inference_job, args=(self.BASE_URL, self.test_image_png))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        end_time = time.time()
        elapsed_time = end_time - start_time
        self.save_time_to_file(f"Time for {num_concurrent_jobs} concurrent inference jobs: {elapsed_time} seconds\n")
        self.assertLessEqual(elapsed_time, 1.1 * T)
        print(f"Time for {num_concurrent_jobs} concurrent inference jobs: {elapsed_time} seconds, while T is {T} seconds")

    def measure_time_for_single_inference_job(self):
        """Measure the time it takes for a single inference job."""
        return measure_time_for_single_inference_job(self.BASE_URL, self.test_image_png)

    def save_time_to_file(self, log_message):
        """Helper method to append measured times to a file."""
        with open("measured_times.log", "a") as log_file:
            log_file.write(log_message)

if __name__ == '__main__':
    unittest.main()
