import os
import random
import string
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from datetime import timezone



from bson.objectid import ObjectId
from datetime import datetime
from app import app, mongo, bcrypt, login_manager, waiting_users_collection
from app.models import User

from . import app, mongo, bcrypt, login_manager
from .models import User
from .utils import fetch_photos_extended, save_image_from_url, merge_images


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
    return ''.join(random.choice(letters_and_digits) for _ in range(length))


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
    print(f'User {current_user.id} is trying to join a game.')
    return render_template('join_game.html')


@app.route('/start-game')
@login_required
def start_game():
    print(f'User {current_user.id} is trying to start a game.')
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
    # Add the current user to the "waiting for a partner" database
    waiting_users_collection.insert_one({"user_id": current_user.id, "timestamp": datetime.now(timezone.utc)})
    
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
        player1 = waiting_users[0] # this is the first player among the two to search for a game

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
        return redirect(url_for('game_ready'))

    # If no match was found yet, redirect to the waiting room for random games
    flash('Waiting for another player to join...')
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

    #         # Cleanup the waiting user entry after the game is found
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
            return redirect(url_for('game_ready'))

        else:
            print(f'User {current_user.id} entered an invalid game code.')
            flash('Invalid or already used game code. Please try again.', 'error')
            return redirect(url_for('enter_code'))

    return render_template('enter_code.html')


# TODO: I think it can be removed.
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
    print(f'User {current_user.id} is trying to load an image.')
    return render_template('load_image.html')


@app.route("/search_photos", methods=["POST"])
def search_photos():
    data = request.get_json()
    query = data.get('query', '')

    # Call the function to get the URLs based on the text query
    photo_urls = fetch_photos_extended(query, amount=10)
    # for photo in photo_urls:
    #     print(photo['url'])
    #     print(photo['alt'])
    #     print('\n')

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
        return jsonify({"status": "error", "message": "Please provide correct answer and distraction answers."})

    # Handle file upload if a file is provided
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Store the uploaded file path in the database
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {f"player_images.{current_user.id}": file_path}}
        )
        print(f"user {current_user.id} uploaded file {file_path}")

    # Handle selected photo URL
    elif selected_photo_url:
        # use save_image_from_url function to save the image locally and continue like with the uploaded file
        #        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename))
        save_image_from_url(selected_photo_url, os.path.join(app.config['UPLOAD_FOLDER'], f'{current_user.id}.jpg'))
        # Store the selected photo URL in the database
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {f"player_images.{current_user.id}": os.path.join(app.config['UPLOAD_FOLDER'],
                                                                       f'{current_user.id}.jpg')}}
        )
        print(f"user {current_user.id} uploaded file {selected_photo_url}")
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
        print("Both players have uploaded/selected images.")
        # use the merge_images function to merge the images
        img1_path = player_images[str(game['player1_id'])]
        img2_path = player_images[str(game['player2_id'])]
        # output path - the combination of the ids plus random string
        output_path = f"{game['player1_id']}_{game['player2_id']}_{generate_game_code(4)}.jpeg"
        merged_image_url = merge_images(img1_path, img2_path, output_path)
        #  update the game document with the merged image URL
        mongo.db.games.update_one(
            {"_id": ObjectId(session['game_id'])},
            {"$set": {"merged_image": merged_image_url}}
        )
        print(f"Images merged successfully. Merged image URL: {merged_image_url[1:]}")
        return jsonify({"status": "ready", "message": "Merged Photo is Ready", "merged_image_url": merged_image_url[1:]})

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
    if game.get("merged_image"):
        return jsonify({"status": "ready", "merged_image_url": game["merged_image"]})

    return jsonify({"status": "waiting", "message": "Still waiting for the other player."})


@app.route('/show_merged_image/<path:merged_image_url>')
@login_required
def show_merged_image(merged_image_url):
    import urllib.parse

    decoded_url = urllib.parse.unquote(merged_image_url)

    # Retrieve the current game document from the database
    game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})

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

    print(decoded_url)
    # Render the page with the merged image and options
    return render_template('guess_image.html', image_url=decoded_url, options=options)


# @app.route('/show_merged_image/<path_image>')
# @login_required
# def show_merged_image(path_image):
#     # import urllib.parse
#
#     # decoded_url = urllib.parse.unquote(merged_image_url)
#
#     # Retrieve the current game document from the database
#     game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})
#
#     # Determine the opponent's ID based on the player ID
#     if game['player1_id'] == current_user.id:
#         opponent_id = game['player2_id']
#     elif game['player2_id'] == current_user.id:
#         opponent_id = game['player1_id']
#     else:
#         return "Error: Current user is not part of this game.", 400
#
#     # Check if the opponent has submitted their answers
#     if 'answers' not in game or str(opponent_id) not in game['answers']:
#         return "Error: Opponent's answers not available.", 400
#
#     # Retrieve the correct answer and distractions
#     correct_answer = game['answers'][str(opponent_id)]["correct"]
#     distractions = game['answers'][str(opponent_id)]["distractions"]
#
#     # Shuffle the options for guessing
#     options = [correct_answer] + distractions
#     random.shuffle(options)
#
#     # print(decoded_url)
#     # Render the page with the merged image and options
#     print(path_image)
#     return render_template('guess_image.html', image_url=path_image, options=options)

# @app.route('/show_merged_image/<merged_image_url>')
# @login_required
# def show_merged_image(merged_image_url):
#     import requests
#     response = requests.get(merged_image_url)
#
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Convert the image content to a PIL Image
#         print("Image successfully retrieved.")
#     else:
#         print("Failed to retrieve the image. Status code:", response.status_code)
#
#     # Retrieve the current game document from the database
#     game = mongo.db.games.find_one({"_id": ObjectId(session['game_id'])})
#
#     # Determine the opponent's ID based on the player ID
#     if game['player1_id'] == current_user.id:
#         opponent_id = game['player2_id']
#     elif game['player2_id'] == current_user.id:
#         opponent_id = game['player1_id']
#     else:
#         return "Error: Current user is not part of this game.", 400
#
#     # Check if the opponent has submitted their answers
#     if 'answers' not in game or str(opponent_id) not in game['answers']:
#         return "Error: Opponent's answers not available.", 400
#
#     # Retrieve the correct answer and distractions
#     correct_answer = game['answers'][str(opponent_id)]["correct"]
#     distractions = game['answers'][str(opponent_id)]["distractions"]
#
#     # Shuffle the options for guessing
#     options = [correct_answer] + distractions
#     random.shuffle(options)
#
#     # Render the page with the merged image and options
#     return render_template('guess_image.html', image_url=merged_image_url, options=options)


@app.route('/submit_guess', methods=['POST'])
@login_required
def submit_guess():
    """
    Handles the guess submission, checks if the guess is correct, and redirects the player with the result.
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

    if guess == correct_answer:
        flash('Congratulations! You guessed correctly!', 'success')
        return redirect(url_for('game_result', result='win'))
    else:
        flash('Sorry, wrong guess. Better luck next time!', 'danger')
        return redirect(url_for('game_result', result='lose'))


@app.route('/game_result/<result>')
@login_required
def game_result(result):
    """
    Displays the result of the game (win/lose).
    """
    return render_template('game_result.html', result=result)
