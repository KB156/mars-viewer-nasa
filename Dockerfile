# Use a slim Python base image
FROM python:3.11-slim

# Install Gunicorn for the production server
RUN pip install flask gunicorn

WORKDIR /app

# Copy the server code
COPY server.py .

# Copy the static folder with all your pre-processed tiles
COPY ./static ./static

EXPOSE 8080

# Run the app with Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8080", "server:app"]