import os
import psycopg2
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


# # Check if the database exists, and if not, create it
# def create_database_if_not_exists():

#     conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS)
#     conn.autocommit = True
#     cur = conn.cursor()
#     cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
#     exists = cur.fetchone()
#     if not exists:
#         # If the database does not exist, create it
#         cur.execute(f"CREATE DATABASE {DB_NAME}")
#     cur.close()
#     conn.close()


# create_database_if_not_exists()


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
