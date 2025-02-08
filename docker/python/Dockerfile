FROM python:3.9-slim

WORKDIR /code

# Install any needed packages
RUN pip install typing-extensions

# Set security limits
RUN mkdir /sandbox && chmod 777 /sandbox
USER nobody
