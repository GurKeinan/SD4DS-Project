import random
import string
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from . import app, mongo, bcrypt, login_manager
from .models import User
from bson.objectid import ObjectId
from datetime import datetime
from app import app, mongo, bcrypt, login_manager, waiting_users_collection
from app.models import User


@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'],
                    str(user_data['_id']))
    return None


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
            "wins": 0,  # TODO tie? or maybe just success?
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
            user = User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'],
                        str(user_data['_id']))
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
        "private": True,  # Since it's a code-based game, it's private by default
        "created_at": datetime.utcnow(),
        "players": [current_user.id]
    }).inserted_id

    # Store the game ID in the session and redirect to the waiting room for created games
    session['game_id'] = str(game_id)
    return redirect(url_for('waiting_room_created_game', game_code=game_code))


@app.route('/waiting-room-created-game')
@login_required
def waiting_room_created_game():
    game_code = request.args.get('game_code')
    return render_template('waiting_room_created_game.html', game_code=game_code)


@app.route('/join-random-game')
@login_required
def join_random_game():
    # Add the current user to the "waiting for a partner" database
    waiting_users_collection.insert_one({"user_id": current_user.id, "timestamp": datetime.utcnow()})

    # Check how many users are currently waiting
    waiting_users = list(waiting_users_collection.find().sort("timestamp"))

    if len(waiting_users) >= 2:
        # If there are at least 2 users, pair them up
        player1 = waiting_users[0]
        player2 = waiting_users[1]

        # Create a new game for them
        game_code = generate_game_code()
        game_id = mongo.db.games.insert_one({
            "game_code": game_code,
            "player1_id": player1["user_id"],
            "player2_id": player2["user_id"],
            "status": "ready",
            "private": False,
            "created_at": datetime.utcnow(),
            "players": [player1["user_id"], player2["user_id"]]
        }).inserted_id

        # Store the game ID in the session for both players
        session['game_id'] = str(game_id)

        # Notify the first player by setting a "game_found" flag
        waiting_users_collection.update_one(
            {"_id": player1['_id']},
            {"$set": {"game_found": True, "game_id": str(game_id)}}
        )

        # Immediately redirect the second player to the game ready page
        waiting_users_collection.delete_one({"_id": player2['_id']})
        return redirect(url_for('game_ready'))

    # If no match was found yet, redirect to the waiting room for random games
    flash('Waiting for another player to join...')
    return redirect(url_for('waiting_room_random_game'))


@app.route('/check-game')
@login_required
def check_game():
    game_id = session.get('game_id')
    if game_id:
        game = mongo.db.games.find_one({"_id": ObjectId(game_id)})
        if game and game['player2_id']:
            return jsonify({"game_found": True})
    else:
        # Check if the current user has been paired up in a game
        waiting_user = waiting_users_collection.find_one({"user_id": current_user.id})
        if waiting_user and waiting_user.get("game_found"):
            session['game_id'] = waiting_user.get("game_id")

            # Cleanup the waiting user entry after the game is found
            waiting_users_collection.delete_one({"_id": waiting_user['_id']})

            return jsonify({"game_found": True})
    return jsonify({"game_found": False})

@app.route('/waiting-room-random-game')
@login_required
def waiting_room_random_game():
    return render_template('waiting_room_random_game.html')


@app.route('/enter-code', methods=['GET', 'POST'])
@login_required
def enter_code():
    if request.method == 'POST':
        game_code = request.form['gameCode']

        # Look for the game in the database using the provided code
        game = mongo.db.games.find_one({"game_code": game_code, "player2_id": None})

        if game:
            # Pair the user with the game
            mongo.db.games.update_one(
                {"_id": game["_id"]},
                {"$set": {"player2_id": current_user.id, "status": "ready"},
                 "$push": {"players": current_user.id}}
            )

            # Redirect both players to the game ready page
            session['game_id'] = str(game['_id'])
            return redirect(url_for('game_ready'))

        else:
            flash('Invalid or already used game code. Please try again.', 'error')
            return redirect(url_for('enter_code'))

    return render_template('enter_code.html')





@app.route('/game-ready')
@login_required
def game_ready():
    game_id = session.get('game_id')
    if game_id:
        game = mongo.db.games.find_one({"_id": ObjectId(game_id)})
        if game:
            return render_template('game_ready.html', game=game)
    return redirect(url_for('home'))


@app.route('/load_image')
def load_image():
    return render_template('load_image.html')

