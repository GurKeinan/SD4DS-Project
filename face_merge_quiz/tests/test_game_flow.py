import json
import os
import time
import unittest

from bson import ObjectId
from flask.testing import FlaskClient
from app import app, mongo, waiting_users_collection
import io


class TestGameFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.testing = True
        cls.test_images_path = os.path.join(os.path.dirname(__file__), 'test_images')


    def setUp(self):
        self.client1 = self.app.test_client()
        self.client2 = self.app.test_client()
        self.client3 = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        mongo.db.users.delete_many({})
        mongo.db.games.delete_many({})
        mongo.db.waiting_users.delete_many({})

    def tearDown(self):
        self.app_context.pop()

    def _signup(self, client: FlaskClient, username, password):
        return client.post('/sign-up', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def _login(self, client: FlaskClient, username, password):
        return client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def _join_random_game(self, client: FlaskClient, user_id):
        return client.post('/join-random-game', data={'user_id': user_id}, follow_redirects=True)

    def _check_random_game(self, client: FlaskClient, user_id):
        return client.post('/check-random-game', data={'user_id': user_id}, follow_redirects=True)

    def _upload_image_and_answers(self, client: FlaskClient, game_id, user_id, image_filename, correct_answer,
                                  distraction1, distraction2):
        image_path = os.path.join(self.test_images_path, image_filename)
        with open(image_path, 'rb') as image_file:
            file_content = image_file.read()

        return client.post('/upload_image', data=dict(
            game_id=game_id,
            user_id=user_id,
            file=(io.BytesIO(file_content), image_filename),
            correct_answer=correct_answer,
            distraction1=distraction1,
            distraction2=distraction2
        ), follow_redirects=True, content_type='multipart/form-data')

    def _make_guess(self, client: FlaskClient, game_id: str, user_id: str, guess: str):
        return client.post('/submit_guess', data=dict(
            game_id=game_id,
            user_id=user_id,
            guess=guess
        ), follow_redirects=True)

    def test_random_game_flow(self):
        # Step 1: Sign up two users
        self._signup(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._signup(self.client2, 'user2', 'password2')
        self.assertEqual(mongo.db.users.count_documents({}), 2)

        # Step 2: Log in both users
        self._login(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._login(self.client2, 'user2', 'password2')

        user1_id = str(mongo.db.users.find_one({'username': 'user1'})['_id'])
        self.assertIsNotNone(user1_id)
        user2_id = str(mongo.db.users.find_one({'username': 'user2'})['_id'])
        self.assertIsNotNone(user2_id)

        # Step 3: Both users join a random game
        player1_join_random_game_response = self._join_random_game(self.client1, user1_id)
        player1_join_random_game_data = json.loads(player1_join_random_game_response.data)
        self.assertEqual(player1_join_random_game_data['message'], 'Waiting for another player to join...')
        # self.assertIn(b'Waiting for another player to join the game', player1_join_random_game_response.data)
        self.assertEqual(waiting_users_collection.count_documents({}), 1) # only one user is waiting for a game

        player2_join_random_game_response = self._join_random_game(self.client2, user2_id)
        self.assertIn(b'Upload a Photo or Choose a Predefined One', player2_join_random_game_response.data)
        # user2 joins the game, the waiting users collection should
        # remain of size 1, as the second user is instantly removed from the waiting users collection
        self.assertEqual(waiting_users_collection.count_documents({}), 1)

        player1_check_random_game_response = self._check_random_game(self.client1, user1_id)  # user1 checks for a game,
        # the waiting users collection should be empty because it finds a game
        self.assertIn(b'{"game_found":true}\n', player1_check_random_game_response.data)
        self.assertEqual(waiting_users_collection.count_documents({}), 0)

        # there should be a game in the mongodb database with both ids
        self.assertEqual(mongo.db.games.count_documents({}), 1)
        game = mongo.db.games.find_one({})
        self.assertTrue(game['player1_id'] == user1_id or game['player2_id'] == user1_id)
        self.assertTrue(game['player1_id'] == user2_id or game['player2_id'] == user2_id)

        # Step 4: Both users upload images and answers
        response1 = self._upload_image_and_answers(
            self.client1, str(game['_id']), user1_id, 'Britney.png', 'Britney', 'Rihanna', 'Beyonce')
        response2 = self._upload_image_and_answers(
            self.client2, str(game['_id']), user2_id, 'Rihanna.png', 'Rihanna', 'Britney', 'Beyonce')

        # Parse the JSON responses
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)

        self.assertEqual(data1['status'], 'waiting')
        self.assertEqual(data2['status'], 'ready')

        # wait until the merged image is created
        time.sleep(15)


        # Step 5: Both users make guesses
        response1 = self._make_guess(self.client1, str(game['_id']), user1_id, 'Rihanna')
        response2 = self._make_guess(self.client2, str(game['_id']), user2_id, 'Beyonce')

        self.assertIn(b'You Win!', response1.data)
        self.assertIn(b'You Lose!', response2.data)

        # Step 6: Verify game results in the database
        user1 = mongo.db.users.find_one({'username': 'user1'})
        user2 = mongo.db.users.find_one({'username': 'user2'})
        self.assertEqual(user1['wins'], 1)
        self.assertEqual(user1['losses'], 0)
        self.assertEqual(user2['wins'], 0)
        self.assertEqual(user2['losses'], 1)

        # Verify that the game has been deleted after completion
        self.assertEqual(mongo.db.games.count_documents({}), 0)

    def _create_game(self, client: FlaskClient, user_id):
        return client.post('/start-game', data={'user_id': user_id}, follow_redirects=True)

    def _waiting_room_created_game(self, client: FlaskClient, user_id, game_code):
        return client.post('/waiting-room-created-game', data={'user_id': user_id, 'game_code': game_code},
                           follow_redirects=True)

    def _check_created_game(self, client: FlaskClient, user_id, game_code):
        return client.post('/check-created-game', data={'user_id': user_id, 'game_code': game_code},
                           follow_redirects=True)

    def _join_created_game(self, client: FlaskClient, user_id, game_code):
        return client.post('/enter-code', data={'user_id': user_id, 'gameCode': game_code}, follow_redirects=True)

    def test_created_game_flow(self):
        # Sign up two users
        self._signup(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._signup(self.client2, 'user2', 'password2')
        self.assertEqual(mongo.db.users.count_documents({}), 2)

        # Log in both users
        self._login(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._login(self.client2, 'user2', 'password2')

        user1_id = str(mongo.db.users.find_one({'username': 'user1'})['_id'])
        user2_id = str(mongo.db.users.find_one({'username': 'user2'})['_id'])

        # User1 creates a game
        create_game_response = self._create_game(self.client1, user1_id)
        create_game_data = json.loads(create_game_response.data)
        self.assertEqual(create_game_data['status'], 'waiting')

        # Extract the game code from the response
        game_code = create_game_data['game_code']
        print(f'GAME CODE: {game_code}')

        # User2 joins the created game
        join_game_response = self._join_created_game(self.client2, user2_id, game_code)
        self.assertIn(b'Upload a Photo or Choose a Predefined One', join_game_response.data)
        print(f'FOUND GAME WITH CODE: {game_code}')

        # check that a game with the given code, ids and ready status exists in the database
        game = mongo.db.games.find_one({'game_code': game_code,
                                        'player1_id': user1_id,
                                        'player2_id': user2_id,
                                        'status': 'ready'})
        self.assertIsNotNone(game)

        # User1 checks if the game is ready
        print(f'CHECKING GAME WITH CODE: {game_code}')
        check_game_response = self._check_created_game(self.client1, user1_id, game_code)
        check_game_data = json.loads(check_game_response.data)
        self.assertTrue(check_game_data['game_found'])

        # Verify that a game exists in the database
        game = mongo.db.games.find_one({'game_code': game_code})
        self.assertIsNotNone(game)
        self.assertEqual(game['player1_id'], user1_id)
        self.assertEqual(game['player2_id'], user2_id)

        # Both users upload images and answers
        response1 = self._upload_image_and_answers(
            self.client1, str(game['_id']), user1_id, 'Britney.png', 'Britney', 'Rihanna', 'Beyonce')
        response2 = self._upload_image_and_answers(
            self.client2, str(game['_id']), user2_id, 'Rihanna.png', 'Rihanna', 'Britney', 'Beyonce')

        # Parse the JSON responses
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)

        self.assertEqual(data1['status'], 'waiting')
        self.assertEqual(data2['status'], 'ready')

        # Wait for the merged image to be created
        time.sleep(15)

        # Both users make guesses
        response1 = self._make_guess(self.client1, str(game['_id']), user1_id, 'Rihanna')
        response2 = self._make_guess(self.client2, str(game['_id']), user2_id, 'Beyonce')

        self.assertIn(b'You Win!', response1.data)
        self.assertIn(b'You Lose!', response2.data)

        # Verify game results in the database
        user1 = mongo.db.users.find_one({'username': 'user1'})
        user2 = mongo.db.users.find_one({'username': 'user2'})
        self.assertEqual(user1['wins'], 1)
        self.assertEqual(user1['losses'], 0)
        self.assertEqual(user2['wins'], 0)
        self.assertEqual(user2['losses'], 1)

        # Verify that the game has been deleted after completion
        self.assertEqual(mongo.db.games.count_documents({}), 0)

    def test_random_game_third_player_not_paired(self):
        # Sign up three users
        self._signup(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._signup(self.client2, 'user2', 'password2')
        time.sleep(1.5)
        self._signup(self.client3, 'user3', 'password3')
        self.assertEqual(mongo.db.users.count_documents({}), 3)

        # Log in all users
        self._login(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._login(self.client2, 'user2', 'password2')
        time.sleep(1.5)
        self._login(self.client3, 'user3', 'password3')

        user1_id = str(mongo.db.users.find_one({'username': 'user1'})['_id'])
        user2_id = str(mongo.db.users.find_one({'username': 'user2'})['_id'])
        user3_id = str(mongo.db.users.find_one({'username': 'user3'})['_id'])

        # User1 and User2 join a random game
        self._join_random_game(self.client1, user1_id)
        join_response = self._join_random_game(self.client2, user2_id)
        self.assertIn(b'Upload a Photo or Choose a Predefined One', join_response.data)

        # Verify that User1 and User2 are paired
        game = mongo.db.games.find_one({})
        self.assertIsNotNone(game)
        self.assertTrue(game['player1_id'] in [user1_id, user2_id])
        self.assertTrue(game['player2_id'] in [user1_id, user2_id])

        # call the check random game endpoint for user1 for cleanup
        self._check_random_game(self.client1, user1_id)
        self.assertEqual(waiting_users_collection.count_documents({}), 0)

        # User3 tries to join a random game
        join_response = self._join_random_game(self.client3, user3_id)

        # Check if the response is a redirect (302 status code)
        if join_response.status_code == 302:
            # If it's a redirect, follow it to get the final response
            join_response = self.client3.get(join_response.location, follow_redirects=True)

        # Now check if the response contains the expected content
        self.assertIn(b'Waiting for another player to join', join_response.data)

        # Verify that User3 is not paired and is in the waiting queue
        self.assertEqual(waiting_users_collection.count_documents({}), 1)
        waiting_user = waiting_users_collection.find_one({})
        self.assertEqual(waiting_user['user_id'], user3_id)

        # Clean up
        mongo.db.games.delete_many({})
        waiting_users_collection.delete_many({})

    def test_join_game_with_wrong_code(self):
        # Sign up two users
        self._signup(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._signup(self.client2, 'user2', 'password2')
        self.assertEqual(mongo.db.users.count_documents({}), 2)

        # Log in both users
        self._login(self.client1, 'user1', 'password1')
        time.sleep(1.5)
        self._login(self.client2, 'user2', 'password2')

        user1_id = str(mongo.db.users.find_one({'username': 'user1'})['_id'])
        user2_id = str(mongo.db.users.find_one({'username': 'user2'})['_id'])

        # User1 creates a game
        create_game_response = self._create_game(self.client1, user1_id)
        create_game_data = json.loads(create_game_response.data)
        correct_game_code = create_game_data['game_code']

        # User2 tries to join with a wrong code
        wrong_game_code = 'WRONG123'
        join_game_response = self._join_created_game(self.client2, user2_id, wrong_game_code)

        # Verify that joining with wrong code fails
        self.assertIn(b'Invalid or already used game code', join_game_response.data)

        # Verify that no game exists with the wrong code
        game_with_wrong_code = mongo.db.games.find_one({'game_code': wrong_game_code})
        self.assertIsNone(game_with_wrong_code)

        # Verify that the correct game still exists
        correct_game = mongo.db.games.find_one({'game_code': correct_game_code})
        self.assertIsNotNone(correct_game)
        self.assertEqual(correct_game['player1_id'], user1_id)
        self.assertIsNone(correct_game['player2_id'])

        # Clean up
        mongo.db.games.delete_many({})