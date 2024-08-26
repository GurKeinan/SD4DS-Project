from flask import request, jsonify, session
from app import app, mongo
import uuid
import threading
from flask import render_template


@app.route('/register', methods=['POST'])
def register():
    # Handle user registration logic
    pass

@app.route('/login', methods=['POST'])
def login():
    # Handle user login logic
    pass

@app.route('/upload_image', methods=['POST'])
def upload_image():
    # Handle image upload and processing logic
    pass

@app.route('/merge_images', methods=['POST'])
def merge_images():
    # Handle image merging logic
    pass

@app.route('/start_game', methods=['POST'])
def start_game():
    # Handle starting a new game between two users
    pass

@app.route('/guess', methods=['POST'])
def guess():
    # Handle a player's guess on the merged image
    pass

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/game')
def game():
    return render_template('game.html')