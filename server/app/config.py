import os

# run [openssl rand -hex 32] in terminal to generate a secret key, then paste them to .env file
# we can talk about this later when the database is properly set up
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
