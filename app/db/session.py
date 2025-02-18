from core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    settings.DATABASE_URL if not settings.TESTING else settings.TEST_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Get a database session.
    Automatically closes the session when the context is exited.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
