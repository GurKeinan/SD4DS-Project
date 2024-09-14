import logging
logging.basicConfig(level=logging.INFO)
import random
import time

import requests
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import threading
import torch
from torchvision import models, transforms
from PIL import Image
# Load ResNet model
from torchvision.models import ResNet50_Weights

start_time = time.time()  # TODO: where should this be defined?




import threading



app = Flask(__name__)


def get_db():
    return MongoClient('mongodb://image-classification-db:27017/')['image_classification']

# Set up MongoDB connection
client = MongoClient('mongodb://image-classification-db:27017/')  # CHECK it is 27017 because it is like that in the docker-compose file?
db = client['image_classification']

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

# def cpu_bound_simulation(n):
#     a, b = 0, 1
#     for _ in range(n):
#         a, b = b, a + b
#     print(f'Finished CPU-bound simulation with n={n}')
#     return a
# def classify_image(filepath):
#     cpu_bound_simulation(1000000)
#     # Dummy implementation, replace with actual model inference
#     return [{'name': 'tomato', 'score': 0.9}, {'name': 'carrot', 'score': 0.02}]

model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
model.eval()

# Load class labels from classes.txt
imagenet_classes_path = os.path.join(os.path.dirname(__file__), 'imagenet-classes.txt')
with open(imagenet_classes_path) as f:
    class_names = [line.strip() for line in f.readlines()]

# Define the image transformation pipeline
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# def classify_image(filepath):
#     with Image.open(filepath) as img:
#         # Convert PNG images (with an alpha channel) to RGB
#         if img.mode == 'RGBA':
#             img = img.convert('RGB')
#
#         # Preprocess the image
#         img_t = preprocess(img)
#         batch_t = torch.unsqueeze(img_t, 0)
#
#         # Perform inference
#         with torch.no_grad():
#             out = model(batch_t)
#
#         # Get the top 5 predictions
#         _, indices = torch.topk(out, 5)
#         percentages = torch.nn.functional.softmax(out, dim=1)[0] * 100
#         predictions = [(class_names[idx], percentages[idx].item()) for idx in indices[0]]
#
#     return [{'name': name, 'score': score / 100} for name, score in predictions]

def classify_image(image_path):
    """
    Classifies an image using Hugging Face Inference API with a ViT model.

    Returns:
    - result (list): A list of dictionaries, each containing the classification label and its score.
                     Example: [{'label': 'tomato', 'score': 0.9}, {'label': 'carrot', 'score': 0.02}]

    Raises:
    - Exception: If there is an error with the request or the classification fails.
    """

    # Hugging Face API URL for the image classification model
    api_url = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"

    # Prepare the request headers with the API token
    headers = {
        "Authorization": f"Bearer {os.environ['HF_API_TOKEN']}"
    }

    try:
        # Open the image file in binary mode and read its content
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        # Send the request to the Hugging Face API
        response = requests.post(api_url, headers=headers, data=image_data)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            result = response.json()
            # this API returns a list of dictionaries, with 'label' and 'score' keys, while we need 'name' and 'score':
            for match in result:
                match['name'] = match.pop('label')

            # Return the classification results
            return result
        else:
            # Raise an exception if the request failed
            raise Exception(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': {'code': 400, 'message': 'No file part'}}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': {'code': 400, 'message': 'No selected file'}}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)

        # Call the classification function
        matches = classify_image(filepath)

        return jsonify({'matches': matches}), 200

    return jsonify({'error': {'code': 400, 'message': 'File type not allowed'}}), 400


@app.route('/async_upload', methods=['POST'])
def async_upload():
    if 'image' not in request.files:
        return jsonify({'error': {'code': 400, 'message': 'No file part'}}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': {'code': 400, 'message': 'No selected file'}}), 400

    if file and allowed_file(file.filename):

        request_id = generate_unique_id()

        filename = secure_filename(str(request_id))
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)


        # Save the request status as 'running'
        db.requests.insert_one({
            'request_id': request_id,
            'status': 'running'
        })

        # Start background processing
        threading.Thread(target=process_image_async, args=(filepath, request_id)).start()

        # process = multiprocessing.Process(target=process_image_async, args=(filepath, request_id))
        # process.start()

        return jsonify({'request_id': request_id}), 202

    return jsonify({'error': {'code': 400, 'message': 'File type not allowed'}}), 400


def process_image_async(filepath, request_id):
    try:
        matches = classify_image(filepath)

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


@app.route('/result/<request_id>', methods=['GET'])
def get_result(request_id):
    try:
        request_id = int(request_id)
        request_data = db.requests.find_one({'request_id': request_id})
    except ValueError:
        return jsonify({'error': {'code': 404, 'message': 'ID not found'}}), 404

    if not request_data:
        return jsonify({'error': {'code': 404, 'message': 'ID not found'}}), 404

    if request_data['status'] == 'running':
        return jsonify({'status': 'running'}), 200

    if request_data['status'] == 'completed':
        return jsonify({
            'status': 'completed',
            'matches': request_data['matches']
        }), 200

    if request_data['status'] == 'error':
        return jsonify({
            'status': 'error',
            'error': request_data['error']
        }), 200  # CHECK: should it be 500?

    print('This should not happen' + 'n'*100)


@app.route('/status', methods=['GET'])
def get_status():
    processed = {
        'success': db.requests.count_documents({'status': 'completed'}),
        'fail': db.requests.count_documents({'status': 'error'}),
        'running': db.requests.count_documents({'status': 'running'}),
        'queued': 0  # Replace it with actual queue status if implemented
    }

    return jsonify({
        'status': {
            'uptime': time.time() - start_time,
            'processed': processed,
            'health': 'ok',
            'api_version': 2
        }
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
