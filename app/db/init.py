from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import create_engine, event
from core.config import settings
from db.base import Base
from db.models import User


def init_db():
    engine = create_engine(settings.DATABASE_URL)

    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database: {engine.url}")

    Base.metadata.create_all(bind=engine)
    print("Created all database tables")

    return engine


def drop_db():
    engine = create_engine(settings.DATABASE_URL)

    if database_exists(engine.url):
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize or drop the database")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creation"
    )

    args = parser.parse_args()

    if args.drop:
        drop_db()

    init_db()
