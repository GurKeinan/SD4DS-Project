# docker-compose build
docker-compose run web python -m tests.test_more_complex
# "python -m unittest discover" runs all tests in the the current directory (including subdirectories),
# but recognizes only files whose names start with "test".
# "docker-compose run web" also starts the db because of the depends_on in docker-compose.yml
# in terminal run:
# chmod +x run_tests.sh  # to make the script executable
# ./run_tests.sh
