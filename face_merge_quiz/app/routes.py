"""
This module contains the routes for the FaceMergeQuiz application.
"""

import os
import random
import base64
from datetime import datetime, timezone
import logging
import requests
from bson.objectid import ObjectId

from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required

from . import app, mongo, bcrypt, login_manager, waiting_users_collection
from .models import User
from .utils import generate_game_code, fetch_photos_extended, save_base64_image, merge_images

# Set up basic logging
logging.basicConfig(level=logging.INFO)


@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'],
                    str(user_data['_id']))
    return None


@app.route('/')
@login_required
def home():
    print(f'user {current_user.id} is in the home page')
    print(f'There are {waiting_users_collection.count_documents({})} users in the waiting room.')
    print(f'there are {mongo.db.games.count_documents({})} games in the database')
    print()

    # Calculate user statistics
    wins = current_user.wins
    losses = current_user.losses
    total_games = wins + losses
    if total_games > 0:
        win_ratio = wins / total_games
        win_percentage = round(win_ratio * 100, 2)
    else:
        win_ratio = 0
        win_percentage = 0

    # Pass statistics to the template
    return render_template(
        'index.html', 
        wins=wins, 
        losses=losses, 
        total_games=total_games, 
        win_percentage=win_percentage
    )



@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_exists = mongo.db.users.find_one({"username": username})
        if user_exists:
            flash('Username already exists. Please choose another one.', 'danger')
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
            user = User(user_data['username'], user_data['password'], user_data['wins'], user_data['losses'],
                        str(user_data['_id']))
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password', 'danger')

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
    print(f'User {current_user.id} is trying to join a game.')
    return render_template('join_game.html')


@app.route('/start-game')
@login_required
def start_game():
    print(f'User {current_user.id} is trying to start a game.')
    # if there is a game created by the user in the database, delete it
    game = mongo.db.games.find_one({"player1_id": current_user.id})
    if game:
        mongo.db.games.delete_one({"_id": game["_id"]})
    # Generate a unique game code
    game_code = generate_game_code()

    # Store the game in the database with the first player (current user)
    game_id = mongo.db.games.insert_one({
        "game_code": game_code,
        "player1_id": current_user.id,
        "player2_id": None,
        "status": "waiting",
        "private": True,  # Since it's a code-based game, it's private by default
        "created_at": datetime.now(timezone.utc),
        "players": [current_user.id]
    }).inserted_id

    # Store the game ID in the session and redirect to the waiting room for created games
    session['game_id'] = str(game_id)
    return redirect(url_for('waiting_room_created_game', game_code=game_code))


@app.route('/waiting-room-created-game')
@login_required
def waiting_room_created_game():
    print(f'User {current_user.id} is in the waiting room for a created game.')
    game_code = request.args.get('game_code')
    return render_template('waiting_room_created_game.html', game_code=game_code)


@app.route('/check-created-game')
@login_required
def check_created_game():
    # search for a game in which this player is the first player
    game_code = request.args.get('game_code')
    print(f'Checking for game with code {game_code}')
    game_id = mongo.db.games.find_one({"player1_id": current_user.id, "status": "ready",
                                       "game_code": game_code})
    if game_id:
        session['game_id'] = str(game_id['_id'])
        # delete this user from the waiting users collection
        waiting_users_collection.delete_one({"user_id": current_user.id})
        print(f'The size of the waiting users collection is \
              {waiting_users_collection.count_documents({})}')
        return jsonify({"game_found": True})

    return jsonify({"game_found": False})


@app.route('/leave-created-game-waiting-room', methods=['POST'])
@login_required
def leave_created_game_waiting_room():
    print(f'User {current_user.id} is trying to leave the waiting room for a created game.')

    # Retrieve the game created by the current user
    game_id = session.get('game_id')
    if game_id:
        game = mongo.db.games.find_one({"_id": ObjectId(game_id), "player1_id": current_user.id, "player2_id": None})

        if game:
            # Delete the game if no second player has joined
            mongo.db.games.delete_one({"_id": game["_id"]})
            session.pop('game_id', None)
            return jsonify({"message": "Game deleted successfully"}), 200

    return jsonify({"message": "Game not found or already joined by another player"}), 404


@app.route('/join-random-game')
@login_required
def join_random_game():
    # If this user already has a record in the waiting users collection, remove it
    waiting_users_collection.delete_one({"user_id": current_user.id})
    # if this user was in any previous game, delete the game
    game = mongo.db.games.find_one({"players": {"$in": [current_user.id]}, "status": "waiting"})
    if game:
        mongo.db.games.delete_one({"_id": game["_id"]})
    # Add the current user to the "waiting for a partner" database
    waiting_users_collection.insert_one({"user_id": current_user.id,
                                         "timestamp": datetime.now(timezone.utc)})

    print(f'User {current_user.id} added to the waiting room.')

    # Check how many users are currently waiting with different ids than the current user
    waiting_users = list(waiting_users_collection.find({"user_id": {"$ne": current_user.id}})
                         .sort("timestamp"))
    # waiting_users = list(waiting_users_collection.find().sort("timestamp"))
    print(f'Found {len(waiting_users)} users in the waiting room.')
    if len(waiting_users) > 0:
        # If there are at least 2 users, pair them up
        print(f'Found {len(waiting_users)} users in the waiting room.')
        print(f'User 1: {current_user.id}, User 2: {waiting_users[0]["user_id"]}')
        player2 = waiting_users_collection.find_one({"user_id": current_user.id})
        player1 = waiting_users[0]  # this is the first player among the two to search for a game

        # Create a new game for them
        game_code = generate_game_code()
        game_id = mongo.db.games.insert_one({
            "game_code": game_code,
            "player1_id": player1["user_id"],
            "player2_id": player2["user_id"],
            "status": "ready",
            "private": False,
            "created_at": datetime.now(timezone.utc),
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
        return redirect(url_for('load_image'))

    # If no match was found yet, redirect to the waiting room for random games
    # flash('Waiting for another player to join...', 'info')
    return redirect(url_for('waiting_room_random_game'))


@app.route('/leave-random-waiting-room', methods=['POST'])
@login_required
def leave_random_waiting_room():
    # Retrieve the current user's waiting record
    waiting_user = waiting_users_collection.find_one({"user_id": current_user.id})
    print(f'User {current_user.id} is trying to leave the waiting room.')

    if waiting_user:
        # Delete the user from the waiting users collection
        waiting_users_collection.delete_one({"user_id": current_user.id})

        # Delete the game associated with the user, if it exists
        game = mongo.db.games.find_one({"players": {"$in": [current_user.id]}, "status": "waiting"})
        if game:
            mongo.db.games.delete_one({"_id": game["_id"]})
            return jsonify({"message": "User and associated game deleted"}), 200

    return jsonify({"message": "User not found in waiting room or no game to delete"}), 404


@app.route('/check-random-game')
@login_required
def check_random_game():
    # search for a game in which this player is the first player
    game_id = mongo.db.games.find_one({"player1_id": current_user.id, "status": "ready"})
    if game_id:
        session['game_id'] = str(game_id['_id'])
        # delete this user from the waiting users collection
        waiting_users_collection.delete_one({"user_id": current_user.id})
        print(f'The size of the waiting users collection is \
              {waiting_users_collection.count_documents({})}')
        return jsonify({"game_found": True})
    # else:
    #     # Check if the current user has been paired up in a game
    #     waiting_user = waiting_users_collection.find_one({"user_id": current_user.id})
    #     if waiting_user and waiting_user.get("game_found"):
    #         session['game_id'] = waiting_user.get("game_id")

    #         # Clean up the waiting user entry after the game is found
    #         waiting_users_collection.delete_one({"_id": waiting_user['_id']})

    #         return jsonify({"game_found": True})
    return jsonify({"game_found": False})


@app.route('/waiting-room-random-game')
@login_required
def waiting_room_random_game():
    print(f'User {current_user.id} is in the waiting room for a random game.')
    return render_template('waiting_room_random_game.html')


@app.route('/enter-code', methods=['GET', 'POST'])
@login_required
def enter_code():
    if request.method == 'POST':
        print(f'User {current_user.id} is trying to enter a game code.')
        game_code = request.form['gameCode']

        # Look for the game in the database using the provided code
        game = mongo.db.games.find_one({"game_code": game_code, "player2_id": None})

        if game:
            print(f'User {current_user.id} joined game with code {game_code}.')
            # Pair the user with the game
            mongo.db.games.update_one(
                {"_id": game["_id"]},
                {"$set": {"player2_id": current_user.id, "status": "ready"},
                 "$push": {"players": current_user.id}}
            )

            # Redirect both players to the game ready page
            session['game_id'] = str(game['_id'])
            return redirect(url_for('load_image'))

        else:
            print(f'User {current_user.id} entered an invalid game code.')
            flash('Invalid or already used game code. Please try again.', 'danger')
            return redirect(url_for('enter_code'))

    return render_template('enter_code.html')


# TODO: remove?
@app.route('/game-ready')
@login_required
def game_ready():
    game_id = session.get('game_id')
    if game_id:
        game = mongo.db.games.find_one({"_id": ObjectId(game_id)})
        if game:
            return render_template('load_image.html', game=game)
    return redirect(url_for('home'))


@app.route('/load_image')
def load_image():
    print(f'User {current_user.id} is trying to load an image.')
    return render_template('load_image.html')


@app.route("/search_photos", methods=["POST"])
def search_photos():
    data = request.get_json()
    query = data.get('query', '')

    # Call the function to get the URLs based on the text query
    photo_urls = fetch_photos_extended(query, amount=10)

    # Return the URLs as a JSON response
    return jsonify({"photos": photo_urls})


@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    file = request.files.get('file')
    selected_photo_url = request.form.get('selected-photo-url')

    # Retrieve answers from form
    correct_answer = request.form.get('correct-answer')
    distraction1 = request.form.get('distraction1')
    distraction2 = request.form.get('distraction2')

    if not correct_answer or not distraction1 or not distraction2:
        return jsonify({"status": "error",
                        "message": "Please provide correct answer and distraction answers."})

    # Handle file upload if a file is provided
    if file:
        file_data = base64.b64encode(file.read()).decode('utf-8')
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {f"player_images.{current_user.id}": file_data}}
        )
        logging.info(f"user {current_user.id} uploaded file using base64 encoding")

    # Handle selected photo URL
    elif selected_photo_url:
        # Download the image and read it into bytes
        response = requests.get(selected_photo_url, timeout=10)
        if response.status_code == 200:
            image_bytes = response.content
            # Optionally, save the image to the file system if needed
            with open(os.path.join(app.config['UPLOAD_FOLDER'], f'{current_user.id}.jpg'), 'wb') as f:
                f.write(image_bytes)
            # Store the image data in base64 in the database
            file_data = base64.b64encode(image_bytes).decode('utf-8')
            mongo.db.games.update_one(
                {"_id": ObjectId(session['game_id'])},
                {"$set": {f"player_images.{current_user.id}": file_data}}
            )
            logging.info(f"user {current_user.id} selected an image from URL and it's stored in base64")
        else:
            return jsonify({"status": "error", "message": "Failed to download image from URL."})
    else:
        return jsonify({"status": "error", "message": "No file or image URL provided."})

    # Store the answers in the database
    mongo.db.games.update_one(
        {"_id": ObjectId(session['game_id'])},
        {"$set": {f"answers.{current_user.id}": {
            "correct": correct_answer,
            "distractions": [distraction1, distraction2]
        }}}
    )

    # Check if both users have uploaded or selected images
    game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})
    player_images = game.get("player_images", {})

    if len(player_images) == 2:  # Both players have uploaded/selected images
        logging.info("Both players have uploaded/selected images.")
        player1_image_data = player_images.get(str(game['player1_id']))
        player2_image_data = player_images.get(str(game['player2_id']))

        # Save the images to the file system
        player1_image_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{game["player1_id"]}.jpg')
        player2_image_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{game["player2_id"]}.jpg')

        save_base64_image(player1_image_data, player1_image_file)
        save_base64_image(player2_image_data, player2_image_file)

        logging.info("player1_image_file=%s", player1_image_file)
        logging.info("player2_image_file=%s", player2_image_file)

        # Send the two images to the Gradio client for merging
        merged_filename = f'{game["_id"]}.jpg'
        merged_image_url = merge_images(player1_image_file, player2_image_file, merged_filename)

        # Save the merged image URL in the database
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {"merged_image": merged_image_url}}
        )

        print(f"Images merged successfully. {merged_image_url=}")
        return jsonify({"status": "ready", "message": "Merged Photo is Ready", "merged_image_url": merged_image_url})

    return jsonify({"status": "waiting", "message": "Waiting for the other player to upload/select their image."})


@app.route('/waiting-for-other')
@login_required
def waiting_for_other():
    return render_template('waiting_for_other_player_to_upload_image.html')


@app.route('/check_merge_ready')
@login_required
def check_merge_ready():
    game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})
    # check if the game document has the merged image URL
    if game:
        if game.get("merged_image"):
            return jsonify({"status": "ready", "merged_image_url": game["merged_image"]})
    else:
        render_template('game_cancelled.html')

    return jsonify({"status": "waiting", "message": "Still waiting for the other player."})


@app.route('/show_merged_image')
@login_required
def show_merged_image():
    # Retrieve the current game document from the database
    game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})

    # retrieve the url of the merged image
    merged_image_url = game.get("merged_image")

    # Determine the opponent's ID based on the player ID
    if game['player1_id'] == current_user.id:
        opponent_id = game['player2_id']
    elif game['player2_id'] == current_user.id:
        opponent_id = game['player1_id']
    else:
        return "Error: Current user is not part of this game.", 400

    # Check if the opponent has submitted their answers
    if 'answers' not in game or str(opponent_id) not in game['answers']:
        return "Error: Opponent's answers not available.", 400

    # Retrieve the correct answer and distractions
    correct_answer = game['answers'][str(opponent_id)]["correct"]
    distractions = game['answers'][str(opponent_id)]["distractions"]

    # Shuffle the options for guessing
    options = [correct_answer] + distractions
    random.shuffle(options)

    print(f'The decoded url show_merged_image sends to the template is {merged_image_url}, '
          f'and the player options are {options}')
    # Render the page with the merged image and options
    print(f'{os.listdir(os.getcwd())=}')
    return render_template('guess_image.html', image_url=merged_image_url, options=options)


@app.route('/submit_guess', methods=['POST'])
@login_required
def submit_guess():
    """
    Handles the guess submission, checks if the guess is correct, 
    and redirects the player with the result.
    """
    guess = request.form.get('guess')

    # Retrieve game data
    game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})

    if game['player1_id'] == current_user.id:
        opponent_id = game['player2_id']
    else:
        opponent_id = game['player1_id']

    # Get the correct answer (provided by the other player)
    correct_answer = game['answers'][str(opponent_id)]['correct']

    # update the game to show that the current user has submitted their guess
    if 'guess_was_submitted' not in game:
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {"guess_was_submitted": 1}}
        )
    else:
        # retrieve the images url in the game and delete them
        # - the images that the players uploaded and the merged image
        player_images = game.get("player_images", {})
        if str(game['player1_id']) in player_images:
            player1_image_file = os.path.join(app.config['UPLOAD_FOLDER'],
                                              f'{game["player1_id"]}.jpg')
            if os.path.exists(player1_image_file):
                os.remove(player1_image_file)
        if str(game['player2_id']) in player_images:
            player2_image_file = os.path.join(app.config['UPLOAD_FOLDER'],
                                              f'{game["player2_id"]}.jpg')
            if os.path.exists(player2_image_file):
                os.remove(player2_image_file)
        if 'merged_image' in game:
            merged_image_file = os.path.join(app.config['OUTPUT_FOLDER'],
                                             f'{game["_id"]}.jpg')
            if os.path.exists(merged_image_file):
                os.remove(merged_image_file)
        # delete the game from the database
        mongo.db.games.delete_one({"_id": game["_id"]})

    if guess == correct_answer:
        # increase the wins of the current user
        mongo.db.users.update_one({"_id": ObjectId(current_user.id)}, {"$inc": {"wins": 1}})
        return redirect(url_for('game_result', result='win'))
    else:
        # increase the losses of the current user
        mongo.db.users.update_one({"_id": ObjectId(current_user.id)}, {"$inc": {"losses": 1}})
        return redirect(url_for('game_result', result='lose'))


@app.route('/game_result/<result>')
@login_required
def game_result(result):
    """
    Displays the result of the game (win/lose).
    """
    return render_template('game_result.html', result=result)


@app.route('/cancel_game', methods=['POST'])
@login_required
def cancel_game():
    print(f'User {current_user.id} is trying to cancel the game.')

    # Find the game where the current user is one of the players
    game = mongo.db.games.find_one({"players": {"$in": [current_user.id]}})

    if game:
        game_id = game["_id"]  # Extract the ObjectId from the game document

        # Update the game status to 'canceled' in the database
        mongo.db.games.update_one({"_id": ObjectId(game_id)}, {"$set": {"status": "canceled"}})
        print(f'Game {game_id} canceled successfully')
        return jsonify({'status': 'canceled'})

    return jsonify({'error': 'Game not found'}), 400


@app.route('/check_game_status', methods=['GET'])
@login_required
def check_game_status():
    game = mongo.db.games.find_one({"players": {"$in": [current_user.id]}})
    if game and game['status'] == 'canceled':
        # delete the game from the database
        mongo.db.games.delete_one({"_id": game["_id"]})
        return jsonify({'status': 'canceled'})
    return jsonify({'status': 'active'})


@app.route('/game_cancelled')
@login_required
def game_cancelled():
    return render_template('game_cancelled.html')
