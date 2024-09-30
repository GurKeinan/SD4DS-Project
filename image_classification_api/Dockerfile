FROM pytorch/pytorch:latest

# The above line is the base image for the docker container.

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .


# we set the environment variable GUNICORN_WORKERS in the docker-compose.yml file

CMD gunicorn -w "$GUNICORN_WORKERS" --threads 6 -b 0.0.0.0:6000 --log-level debug app:app

