FROM python:3.11-alpine

WORKDIR /app

# Install Docker client
RUN apk add --no-cache docker-cli

# Copy Docker environment files
COPY docker/python/Dockerfile docker/python/
COPY docker/java/Dockerfile docker/java/
COPY docker/cpp/Dockerfile docker/cpp/

# Build execution environment images
RUN docker build -t beatcode-python:latest docker/python/ && \
    docker build -t beatcode-java:latest docker/java/ && \
    docker build -t beatcode-cpp:latest docker/cpp/

# Continue with app setup
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
