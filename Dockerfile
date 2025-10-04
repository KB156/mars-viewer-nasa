# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install all packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Tell Docker that the container listens on port 8080
EXPOSE 8080

# Define the command to run your app using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "server:app"]