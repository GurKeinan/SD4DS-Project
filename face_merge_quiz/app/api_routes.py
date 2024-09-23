import os

import requests
from flask import flash, redirect, url_for, render_template, request

from . import app, mongo, bcrypt, login_manager
from flask_login import login_required
from .models import User
from bson.objectid import ObjectId

import logging
logging.basicConfig(level=logging.INFO)

BASE_URL = 'http://face-merge-image-classification-api:6000'

# Custom unauthorized handler
@login_manager.unauthorized_handler
def unauthorized():
    flash('Please log in to access this page.', 'danger')
    return redirect(url_for('login'))
@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'],
                    str(user_data['_id']))
    return None



@app.route('/api/status')
@login_required
def api_status():
    response = requests.get(f'{BASE_URL}/status')
    return render_template('api/status.html', status=response.json())


@app.route('/api/upload_image', methods=['GET', 'POST'])
@login_required
def api_upload_image():
    if request.method == 'POST':
        return _post_request_to_api(request, 'upload_image')
    return render_template('api/upload_image.html')


@app.route('/api/async_upload', methods=['GET', 'POST'])
@login_required
def api_async_upload():
    if request.method == 'POST':
        return _post_request_to_api(request, 'async_upload')
    return render_template('api/async_upload.html')

def _post_request_to_api(request_from_web, endpoint):
    assert request_from_web.method == 'POST'
    files = None

    # the request is a POST request with form data, which was appended in js: formData.append('image', fileInput);
    if 'image' in request.files:
        # Make sure to pass the file stream properly
        image = request.files['image']
        files = {'image': (image.filename, image.stream, image.content_type)}

    elif 'selected-photo-url' in request.form:
        selected_photo_url = request.form['selected-photo-url']
        if selected_photo_url.startswith('/static/'):
            # This is a predefined image, we need to get its full path
            image_path = os.path.join(app.root_path, selected_photo_url.lstrip('/'))
            # Use 'with' to open the file, ensuring it stays open during the POST request
            with open(image_path, 'rb') as f:
                files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
                # Make the request inside the 'with' block so the file is still open
                response = requests.post(f'{BASE_URL}/{endpoint}', files=files)
                return response.json()

    # If no files were found or post failed, return an error
    if files:
        response = requests.post(f'{BASE_URL}/{endpoint}', files=files)
        return response.json()
    else:
        return "No image provided", 400

@app.route('/api/result', methods=['GET', 'POST'])
@login_required
def api_result():
    if request.method == 'POST':
        request_id = request.form['request_id']
        response = requests.get(f'{BASE_URL}/result/{request_id}')
        logging.info(f'{response.json()=}')
        return response.json()
    return render_template('api/result.html')
