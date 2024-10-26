import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
## Create an .env file in the same hierarchy as the .gitignore file
## Inside the .env file, add the following:
## DB_HOST=localhost
## DB_PORT=5432
## DB_NAME=Beatcode
## DB_USER=postgres
## DB_PASS=[Depend on your password for now]
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Reuse the same database management logic in all routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
