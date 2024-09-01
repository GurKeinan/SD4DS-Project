import random
import string
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from bson.objectid import ObjectId
from datetime import datetime
from app import app, mongo, bcrypt, login_manager
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'], str(user_data['_id']))
    return None

# Function to generate a random game code
def generate_game_code(length=6):
    """Generates a random game code."""
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_exists = mongo.db.users.find_one({"username": username})
        if user_exists:
            flash('Username already exists!', 'error')
            return redirect(url_for('sign_up'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user_id = mongo.db.users.insert_one({
            "username": username,
            "password": hashed_password,
            "wins": 0,
            "losses": 0
        }).inserted_id

        new_user = User(username, hashed_password, _id=str(user_id))
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('sign_up.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = mongo.db.users.find_one({"username": username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'], str(user_data['_id']))
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/join-game')
@login_required
def join_game():
    return render_template('join_game.html')

@app.route('/start-game')
@login_required
def start_game():
    # Generate a unique game code
    game_code = generate_game_code()

    # Store the game in the database with the first player (current user)
    game_id = mongo.db.games.insert_one({
        "game_code": game_code,
        "player1_id": current_user.id,
        "player2_id": None,
        "status": "waiting",
        "private": False,
        "created_at": datetime.utcnow(),
        "players": [current_user.id]
    }).inserted_id

    session['game_id'] = str(game_id)
    flash('Game created successfully!', 'success')
    return render_template('new_game_code.html', game_code=game_code)

@app.route('/waiting-room', methods=['POST'])
@login_required
def waiting_room():
    game_code = request.form['game_code']

    # Retrieve the game from the database using the game code and current user's ID
    game = mongo.db.games.find_one({"game_code": game_code, "player1_id": current_user.id})

    if game:
        # Render the waiting room and pass the game code to the template
        return render_template('waiting_room.html', game_code=game_code)
    else:
        # Handle the error if the game is not found or if the user doesn't match
        flash('Error finding the game. Please try again.', 'error')
        return redirect(url_for('home'))

@app.route('/join-game-code', methods=['POST'])
@login_required
def join_game_code():
    game_code = request.form['gameCode']

    # Asynchronously check if the game code exists in the database
    game = mongo.db.games.find_one({"game_code": game_code})

    if game:
        if game['player2_id'] is None:
            # Update the game with the second player's ID
            mongo.db.games.update_one(
                {"_id": game['_id']},
                {"$set": {"player2_id": current_user.id, "status": "ready"},
                 "$push": {"players": current_user.id}}
            )
            session['game_id'] = str(game['_id'])
            # Notify the first player and redirect both to the load_image page
            return redirect(url_for('game_ready'))
        else:
            flash('This game is already in progress.', 'error')
            return redirect(url_for('join_game'))
    else:
        flash('Invalid game code. Please try again.', 'error')
        return redirect(url_for('join_game'))

@app.route('/join-random-game')
@login_required
def join_random_game():
    # Try to find a public game where player2_id is None (waiting for a second player)
    game = mongo.db.games.find_one({"private": False, "player2_id": None})

    if game:
        # Found an available game, add the current user as the second player
        mongo.db.games.update_one(
            {"_id": game["_id"]},
            {"$set": {"player2_id": current_user.id, "status": "ready"},
             "$push": {"players": current_user.id}}
        )
        session['game_id'] = str(game['_id'])
        # Notify the first player and redirect both to the load_image page
        return redirect(url_for('game_ready'))
    else:
        # No public games available, move to the waiting room
        return render_template('waiting_room.html', game_code=None)

@app.route('/check-game')
@login_required
def check_game():
    game_id = session.get('game_id')
    if game_id:
        game = mongo.db.games.find_one({"_id": ObjectId(game_id)})
        if game and game['player2_id']:
            return jsonify({"game_found": True})
    return jsonify({"game_found": False})

@app.route('/enter-code')
@login_required
def enter_code():
    return render_template('enter_code.html')

@app.route('/game-ready')
@login_required
def game_ready():
    game_id = session.get('game_id')
    if not game_id:
        flash('No game found.', 'error')
        return redirect(url_for('home'))

    game = mongo.db.games.find_one({"_id": ObjectId(game_id)})
    if game:
        # Notify all players and redirect to the game page
        return render_template('load_image.html', players=game['players'])
    else:
        flash('Game no longer exists.', 'error')
        return redirect(url_for('home'))