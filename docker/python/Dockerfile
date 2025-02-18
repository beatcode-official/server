FROM python:3.9-slim

WORKDIR /code

# Install any needed packages
RUN pip install typing-extensions

# Set security limits
RUN useradd -m player
RUN chown -R player:player /code
RUN chmod -R 777 /code
USER player
