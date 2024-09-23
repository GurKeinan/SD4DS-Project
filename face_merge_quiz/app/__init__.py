from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from gradio_client import Client
import httpx
import os
import logging

from . import routes, api_routes

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # TODO change this
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')  # MongoDB URI
# app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV')  # TODO: we need this?
app.config['UPLOAD_FOLDER'] = 'app/static/uploads/'
app.config['OUTPUT_FOLDER'] = 'app/static/outputs/'

logging.info(f"MongoDB URI: {app.config['MONGO_URI']}")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize Flask extensions
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Set the timeout for HTTP requests using httpx.Timeout
timeout = httpx.Timeout(120)  # Total timeout in seconds

# Initialize the face-swap Client with the timeout
face_swap_client = Client(
    "felixrosberg/face-swap",
    httpx_kwargs={"timeout": timeout}
)

waiting_users_collection = mongo.db.waiting_users  # New collection for waiting users


@app.context_processor
def inject_user():
    return dict(user=current_user)
