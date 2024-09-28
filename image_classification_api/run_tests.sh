# Run tests that check the image classification API

# Start containers in detached mode
docker-compose up -d

# Wait for 3 seconds to give the containers time to start
sleep 3

# Run the tests
python -m unittest discover

# Stop and remove the containers
docker-compose down


# Note: if needed, run the following command to make this script executable
# chmod +x run_tests.sh

