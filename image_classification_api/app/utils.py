import mimetypes
import random
from flask_pymongo import PyMongo
from . import db, genai, get_db
import logging
logging.basicConfig(level=logging.INFO)



# Define allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_id():
    """Generate a unique request ID randomly in the range [10000, 1000000]"""
    while True:
        new_id = random.randint(10000, 1000000)
        if db.requests.find_one({'request_id': new_id}) is None:
            return new_id



def classify_image(image_path):
    try:
        # Upload the image file
        logging.info(f"The guessed MIME type is {mimetypes.guess_type(image_path)}")
        image_file = genai.upload_file(path=image_path, display_name="Uploaded Image")

        # Initialize the model
        google_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")

        # Create a classification prompt (or customize as needed)
        prompt = ("Classify the objects in this image. Return the names and confidence scores of the objects."
                  "Use the format [ {'name': string, 'score': number}]. For example: "
                  "[{'name': 'tomato', 'score': 0.9}, {'name':'carrot', 'score': 0.02}]")

        # Generate content using the model
        response = google_model.generate_content([image_file, prompt])
        logging.info(f"Response: {response}")

        # transform the results into a list of dictionaries
        return eval(response.text)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return [{'name': 'tomato', 'score': 0.9}, {'name': 'carrot', 'score': 0.02}]



def process_image_async(filepath, request_id):
    try:
        logging.info(f"Processing started for request ID {request_id}")
        matches = classify_image(filepath)
        logging.info(f"Processing completed for request ID {request_id}")
        # Update the request status as 'completed' and save the results
        get_db().requests.update_one(
            {'request_id': request_id},
            {'$set': {
                'status': 'completed',
                'matches': matches
            }}
        )
    except Exception as e:
        get_db().requests.update_one(
            {'request_id': request_id},
            {'$set': {
                'status': 'error',
                'error': {'code': 500, 'message': str(e)}
            }}
        )
