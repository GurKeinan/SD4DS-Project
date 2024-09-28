# FaceMergeQuiz - Final Project in Software Development for Data Science
## Team Members
- Gur Keinan 213635899
- Idan Pipano 213495260
- Itamar Reinman 3269935285

## Project Description
The project contains two functionalities:
1. API for image classification which can handle both synchronous and asynchronous requests.
2. A multi-player quiz game where 2 players are asked to upload pictures of people and the game will merge the faces of the two people in the pictures and will make the players guess who are the people in the merged picture.

## Project Structure
The project is structured as follows:

## Project Structure

```
SD4DS Project
├── image_classification_api
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── download_weights.py
│   ├── tests
│   │   ├── test_stress.py
│   │   ├── __init__.py
│   │   ├── test_post_async_upload.py
│   │   ├── test_post_async_upload_and_get_result.py
│   │   ├── test_get_result.py
│   │   ├── test_post_upload_image.py
│   │   ├── test_get_status.py
│   │   ├── test_base.py
│   │   └── assets
│   │       ├── britney.png
│   │       └── test_img.jpeg
│   ├── .dockerignore
│   ├── run_tests.sh
│   ├── app.py
│   ├── docker-compose.yml
│   └── imagenet-classes.txt
├── README.md
├── face_merge_quiz
│   ├── app
│   │   ├── models.py
│   │   ├── __init__.py
│   │   ├── api_routes.py
│   │   ├── utils.py
│   │   ├── static
│   │   │   ├── js
│   │   │   │   ├── show_predefined_images.js
│   │   │   │   └── convert_json_to_table.js
│   │   │   ├── uploads
│   │   │   ├── predefined-images
│   │   │   │   ├── Itamar.jpg
│   │   │   │   ├── Gur.png
│   │   │   │   ├── Idan.png
│   │   │   │   ├── Ori.png
│   │   │   │   ├── Noam.png
│   │   │   │   └── Stav.png
│   │   │   └── outputs
│   │   ├── templates
│   │   │   ├── navbar.html
│   │   │   ├── index.html
│   │   │   ├── enter_code.html
│   │   │   ├── game_cancelled.html
│   │   │   ├── login.html
│   │   │   ├── join_game.html
│   │   │   ├── load_image.html
│   │   │   ├── flashed_messages.html
│   │   │   ├── new_game.html
│   │   │   ├── game_result.html
│   │   │   ├── api
│   │   │   │   ├── status.html
│   │   │   │   ├── async_upload.html
│   │   │   │   ├── result.html
│   │   │   │   └── upload_image.html
│   │   │   ├── new_game_code.html
│   │   │   ├── waiting_for_other_player_to_upload_image.html
│   │   │   ├── waiting_room_random_game.html
│   │   │   ├── sign_up.html
│   │   │   ├── guess_image.html
│   │   │   └── waiting_room_created_game.html
│   │   ├── routes.py
│   │   └── search_engine_key.csv
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── tests
│   │   ├── test_images
│   │   │   ├── Rihanna.png
│   │   │   └── Britney.png
│   │   ├── app
│   │   │   └── static
│   │   │       ├── uploads
│   │   │       └── outputs
│   │   ├── test_login.py
│   │   ├── __init__.py
│   │   └── test_game_flow.py
│   ├── .dockerignore
│   ├── run_tests.sh
│   ├── .env
│   ├── docker-compose.test.yml
│   ├── run_debug.sh
│   └── docker-compose.debug.yml
├── .gitignore
└── docker-compose.yml
```

## Running the Project
To run the project, follow these steps:
1. Clone the repository.
2. Ensure that Docker is installed on your machine.
3. Run the following command in the terminal from inside the main directory of the project:
```bash
docker-compose up --build
```
- The API endpoints will be available from the application - you can enter the relevant page from the navigation bar.

## Testing the Project
- To test the API, run the following command in the terminal from inside the directory 'image_classification_api':
```bash
./run_tests.sh
```
- To test the quiz game, run the following command in the terminal from inside the directory 'face_merge_quiz':
```bash
./run_tests.sh
```

## Playing the Quiz Game
The game flow can be divided into the following steps:
1. Pairing up players for the game.
   - Option 1 - join via code: the first player will create a game and will receive a code. The second player will join the game by entering the code.
   - Option 2 - join via waiting room: the first player will enter the waiting room and will wait for another player to join.
2. Uploading images: each player will upload an image of a person.
   - Option 1 - upload an image from a local file on the device.
   - Option 2 - search a celebrity image by name in the app's built-in search engine.
   - Option 3 - choose one of the predefined images in the app.
3. Enter right answer and distractions: each player will enter the name of the person in the image they uploaded and will enter 2 distractions.
4. Merging the images: the app will merge the faces of the two people in the images using Hugging Face's model.
5. Guessing the people in the merged image: each player will guess who are the people in the merged image.
6. Scoring: the players will receive points based on the correctness of their answers.
