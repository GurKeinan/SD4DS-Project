#FLASK_ENV=testing \
#MONGO_URI=mongodb://face-merge-mongodb:27017/testdb \
#docker-compose \
#-f docker-compose.override.yml \
#up

docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit






## To run the tests outside the container
#python -m unittest discover tests
#
## in terminal run:
## chmod +x run_tests.sh  # to make the script executable
## ./run_tests.sh
#
#
## "python -m unittest discover <dir>" runs all tests in <dir>> (including subdirectories),
## but recognizes only files whose names start with "test".
