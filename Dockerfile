# Use the latest Python 3.10 slim-buster image
FROM python:3.10.8-slim-buster

# Update and install essential packages
RUN apt-get update -y && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends ffmpeg python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the application code into the container
COPY . /app/
WORKDIR /app/

# Install the Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose port 8000 for Gunicorn
EXPOSE 8000

# Command to start the application using gunicorn and run the bot
CMD gunicorn --bind 0.0.0.0:8000 app:app & python3 lncrawl --bot telegram
