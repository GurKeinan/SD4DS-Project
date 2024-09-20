#docker-compose -f docker-compose.debug.yml up --build


# in case of "network not found" error
docker-compose down
docker volume prune
docker-compose -f docker-compose.debug.yml up --build --force-recreate










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
