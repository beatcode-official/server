# Use the specified Docker image from the environment
ARG DOCKER_IMAGE=python:3.11-alpine
FROM ${DOCKER_IMAGE}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
