FROM python:3.10-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Set environment variable to ensure Python does not buffer output
ENV PYTHONUNBUFFERED=1

# Run Gunicorn with captured output for better logging visibility
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--capture-output", "--log-level", "debug", "app:app"]
