# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (including git, Calibre, and necessary libraries)
RUN apt-get update && apt-get install -y \
    git \
    calibre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/prasadghanwat12/lightcrawler.git /app/lightnovel-crawler

# Change the working directory to the cloned repository
WORKDIR /app/lightnovel-crawler

# Install required Python dependencies, including Flask and gunicorn
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install flask \
    && pip install gunicorn

# Expose any required ports (optional)
EXPOSE 8000

# Start gunicorn to serve the Flask app and run the bot
CMD gunicorn app:app --bind 0.0.0.0:8000 & python3 lncrawl --bot telegram
