FROM pytorch/pytorch:latest

# The above line is the base image for the docker container.

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN python download_weights.py

CMD ["gunicorn", "-w", "8", "-b", "0.0.0.0:5000", "app:app"]
#CMD ["python", "-m", "tests.get_status"]

