# docker-compose build
docker-compose run web python -m tests.get_status
# this also starts the db because of the depends_on in docker-compose.yml

# in terminal run:
# chmod +x run_tests.sh  # to make the script executable
# ./run_tests.sh
