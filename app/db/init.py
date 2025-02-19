import json
import subprocess

from core.config import settings
from db.base import Base
from db.models.problem import Problem, Boilerplate, CompareFunc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists


def run_migrations():
    """Run Alembic migrations to ensure the schema is up to date."""
    try:
        subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "auto"], check=True
        )
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print("Generated and applied database migrations successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        raise


def init_db(test=False):
    """Initialize the database and insert initial data if needed."""
    engine = create_engine(
        settings.DATABASE_URL if not test else settings.TEST_DATABASE_URL
    )

    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database: {engine.url}")

    run_migrations()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        with open("db/combined.json", "r") as file:
            problems = json.load(file)

        for problem in problems:
            new_problem = Problem(
                title=problem["title"],
                source=problem["source"],
                description=problem["description"],
                explanation=problem["explanation"],
                difficulty=problem["difficulty"],
                sample_test_cases=problem["sample_test_cases"],
                sample_test_results=problem["sample_test_results"],
                hidden_test_cases=problem["hidden_test_cases"],
                hidden_test_results=problem["hidden_test_results"],
                method_name=problem["method_name"],
            )

            new_boilerplate = Boilerplate(
                java=problem["boilerplate"]["java"],
                cpp=problem["boilerplate"]["cpp"],
                python=problem["boilerplate"]["python"],
            )

            new_compare_func = CompareFunc(
                java=problem["compare_func"]["java"],
                cpp=problem["compare_func"]["cpp"],
                python=problem["compare_func"]["python"],
            )

            new_problem.boilerplate = new_boilerplate
            new_problem.compare_func = new_compare_func

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


def drop_all_db(test=False):
    """Drop all tables in the database."""
    engine = create_engine(
        settings.DATABASE_URL if not test else settings.TEST_DATABASE_URL
    )

    if database_exists(engine.url):
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables")


def drop_db(table_names, test=False):
    """Drop specific tables in the database. (--drop=table1,table2)"""
    engine = create_engine(
        settings.DATABASE_URL if not test else settings.TEST_DATABASE_URL
    )
    if database_exists(engine.url):
        table_list = [Base.metadata.tables[name] for name in table_names.split(",")]
        Base.metadata.drop_all(bind=engine, tables=table_list)
        print(f"Dropped tables: {table_names}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dropall", action="store_true", help="Drop existing tables before creation"
    )

    parser.add_argument(
        "--drop",
        type=str,
        help="Drop specific tables (comma-separated, ex: --drop=table1,table2)",
    )

    parser.add_argument(
        "--droptest",
        action="store_true",
        help="Drop existing test tables before creation",
    )

    args = parser.parse_args()

    if args.dropall:
        drop_all_db()
    if args.drop:
        drop_db(args.drop)
    if args.droptest:
        drop_all_db(test=True)

    init_db()
    init_db(test=True)
