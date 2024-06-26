# Use Python base image
FROM python:3.11.9-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the current directory into the container at /app
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip3 install -r requirements.txt

# Set the default command to run when the container starts
CMD uvicorn app:app --host 0.0.0.0 --port $PORT