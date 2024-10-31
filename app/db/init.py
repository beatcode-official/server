import json

from core.config import settings
from db.base import Base
from db.models import Problem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists


def init_db():
    engine = create_engine(settings.DATABASE_URL)

    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database: {engine.url}")

    Base.metadata.create_all(bind=engine)
    print("Created all database tables")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        with open('db/combined.json', 'r') as file:
            problems = json.load(file)

        for problem in problems:
            new_problem = Problem(
                title=problem['title'],
                description=problem['description'],
                difficulty=problem['difficulty'],
                sample_test_cases=problem['sample_test_cases'],
                sample_test_results=problem['sample_test_results'],
                hidden_test_cases=problem['hidden_test_cases'],
                hidden_test_results=problem['hidden_test_results'],
                boilerplate=problem['boilerplate'],
                compare_func=problem['compare_func']
            )

            session.add(new_problem)

        session.commit()
        print("Problem data inserted successfully!")

    except Exception as e:
        print(f"Error inserting data: {e}")
        session.rollback()
        raise
    finally:
        session.close()

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
