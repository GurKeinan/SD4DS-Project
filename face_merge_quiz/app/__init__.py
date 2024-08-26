from flask import Flask
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://face-merge-mongodb:27017/face_merge_db"
mongo = PyMongo(app)

from app import routes
