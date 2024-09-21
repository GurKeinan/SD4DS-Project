import requests
from flask import flash, redirect, url_for, render_template

from . import app, mongo, bcrypt, login_manager
from flask_login import login_required
from .models import User
from bson.objectid import ObjectId

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
    response = requests.get('http://face-merge-image-classification-api:6000/status')
    return render_template('api/status.html', status=response.json())


@app.route('/api/upload_image')
@login_required
def api_upload_image():
    return render_template('api/upload_image.html')

