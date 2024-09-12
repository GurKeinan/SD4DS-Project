from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from gradio_client import Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MONGO_URI'] = 'mongodb://face-merge-mongodb:27017/face_merge_db'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['OUTPUT_FOLDER'] = 'static/outputs/'

# Initialize Flask extensions
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the face-swap Client once
face_swap_client = Client("felixrosberg/face-swap")

waiting_users_collection = mongo.db.waiting_users  # New collection for waiting users

from . import routes

@app.context_processor
def inject_user():
    return dict(user=current_user)
