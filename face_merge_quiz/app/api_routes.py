import requests
from . import app, mongo, bcrypt, login_manager
from flask_login import login_required
from .models import User
from bson.objectid import ObjectId


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
    return "The response from our API server is:" + response.text, response.status_code, response.headers.items()