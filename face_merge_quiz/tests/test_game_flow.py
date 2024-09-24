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

    def test_game_flow(self):
        # Step 1: Sign up two users
        self._signup(self.client1, 'user1', 'password1')
        self._signup(self.client2, 'user2', 'password2')
        self.assertEqual(mongo.db.users.count_documents({}), 2)

        # Step 2: Log in both users
        self._login(self.client1, 'user1', 'password1')
        self._login(self.client2, 'user2', 'password2')

        user1_id = str(mongo.db.users.find_one({'username': 'user1'})['_id'])
        self.assertIsNotNone(user1_id)
        user2_id = str(mongo.db.users.find_one({'username': 'user2'})['_id'])
        self.assertIsNotNone(user2_id)

        # Step 3: Both users join a random game
        player1_join_random_game_response = self._join_random_game(self.client1, user1_id)
        self.assertIn(b'Waiting for another player to join the game', player1_join_random_game_response.data)
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