import requests
from flask import flash, redirect, url_for, render_template, request

from . import app, mongo, login_manager
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
        # the request is a POST request with form data, which was appended in js: formData.append('image', fileInput);
        files = {
            'image': (request.files['image'].filename, request.files['image'], request.files['image'].content_type)}

        # post the image to the image classification API, with content-type image/jpeg or image/png and
        # content-disposition form-data; name="image"; filename=whatever
        response = requests.post(f'{BASE_URL}/upload_image', files=files)
        return response.json()
    return render_template('api/upload_image.html')


@app.route('/api/async_upload', methods=['GET', 'POST'])
@login_required
def api_async_upload():
    if request.method == 'POST':
        # the request is a POST request with form data, which was appended in js: formData.append('image', fileInput);
        files = {
            'image': (request.files['image'].filename, request.files['image'], request.files['image'].content_type)}

        # post the image to the image classification API, with content-type image/jpeg or image/png and
        # content-disposition form-data; name="image"; filename=whatever
        response = requests.post(f'{BASE_URL}/async_upload', files=files)
        return str(response.json()['request_id'])
    return render_template('api/async_upload.html')


@app.route('/api/result', methods=['GET', 'POST'])
@login_required
def api_result():
    if request.method == 'POST':
        request_id = request.form['request_id']
        response = requests.get(f'{BASE_URL}/result/{request_id}')
        logging.info(f'{response.json()=}')
        return response.json()
    return render_template('api/result.html')
