import time

from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from pymongo import MongoClient
import uuid
import threading
import torch
from torchvision import models, transforms
from PIL import Image

start_time = time.time() # TODO: where should this be defined?


# Load ResNet model
model = models.resnet50(pretrained=True)
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

app = Flask(__name__)

# Set up MongoDB connection
client = MongoClient('mongodb://image-classification-db:27017/')
db = client['image_classification']

# Define allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def classify_image(filepath):
#     # Dummy implementation, replace with actual model inference
#     return [{'name': 'tomato', 'score': 0.9}, {'name': 'carrot', 'score': 0.02}]

def classify_image(filepath):
    # Open the image file
    img = Image.open(filepath)
    
    # Preprocess the image
    img_t = preprocess(img)
    batch_t = torch.unsqueeze(img_t, 0)

    # Perform inference
    with torch.no_grad():
        out = model(batch_t)
    
    # Get the top 5 predictions
    _, indices = torch.topk(out, 5)
    percentages = torch.nn.functional.softmax(out, dim=1)[0] * 100
    predictions = [(class_names[idx], percentages[idx].item()) for idx in indices[0]]

    # Return the predictions in the expected format
    return [{'name': name, 'score': score / 100} for name, score in predictions]

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
        filename = secure_filename(file.filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)
        
        request_id = str(uuid.uuid4())
        
        # Save the request status as 'running'
        db.requests.insert_one({
            'request_id': request_id,
            'status': 'running'
        })
        
        # Start background processing
        threading.Thread(target=process_image_async, args=(filepath, request_id)).start()
        
        return jsonify({'request_id': request_id}), 202
    
    return jsonify({'error': {'code': 400, 'message': 'File type not allowed'}}), 400

def process_image_async(filepath, request_id):
    try:
        matches = classify_image(filepath)
        
        # Update the request status as 'completed' and save the results
        db.requests.update_one(
            {'request_id': request_id},
            {'$set': {
                'status': 'completed',
                'matches': matches
            }}
        )
    except Exception as e:
        db.requests.update_one(
            {'request_id': request_id},
            {'$set': {
                'status': 'error',
                'error': {'code': 500, 'message': str(e)}
            }}
        )

@app.route('/result/<request_id>', methods=['GET'])
def get_result(request_id):
    request_data = db.requests.find_one({'request_id': request_id})
    
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
        }), 200

@app.route('/status', methods=['GET'])
def get_status():
    processed = {
        'success': db.requests.count_documents({'status': 'completed'}),
        'fail': db.requests.count_documents({'status': 'error'}),
        'running': db.requests.count_documents({'status': 'running'}),
        'queued': 0  # Replace with actual queue status if implemented
    }

    return jsonify({  # TODO: make sure that jsonify means that the server will have Content-Type: application/json
        'status': {
            'uptime': time.time() - start_time,
            'processed': processed,
            'health': 'ok',
            'api_version': 2
        }
    }), 200


if __name__ == '__main__':
    print('hiiiiiiiiiiiiiiii the if __name__ == __main__ is running')
    app.run(host='0.0.0.0', port=5001)
