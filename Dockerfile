# Build images first
FROM docker:latest AS builder

WORKDIR /build

COPY docker/python/ docker/python/
COPY docker/java/ docker/java/
COPY docker/cpp/ docker/cpp/

RUN docker build -t beatcode-python:latest docker/python/ && \
    docker build -t beatcode-java:latest docker/java/ && \
    docker build -t beatcode-cpp:latest docker/cpp/

# Set up the server
FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
