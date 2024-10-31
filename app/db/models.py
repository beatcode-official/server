from sqlalchemy import ARRAY, Boolean, CheckConstraint, Column, DateTime, Enum, Float, Integer, String, Text
from db.base import Base
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from services.email import generate_token


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    rating = Column(Float, default=0)  # NOTE: for future ranked matches
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, nullable=True)
    reset_token = Column(String, unique=True, nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    token_secret = Column(String, nullable=True, server_default=generate_token())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DifficultyLevel(str, PyEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)  # HTML Format
    difficulty = Column(
        Enum(DifficultyLevel),
        nullable=False,
        index=True
    )
    time_limit_ms = Column(Integer, nullable=False)
    memory_limit_mb = Column(Integer, nullable=False)
    sample_test_cases = Column(ARRAY(String), nullable=False)
    sample_test_results = Column(ARRAY(String), nullable=False)
    hidden_test_cases = Column(ARRAY(String), nullable=False)
    hidden_test_results = Column(ARRAY(String), nullable=False)
    boilerplate = Column(Text, nullable=False)
    compare_func = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            'array_length(sample_test_cases, 1) = array_length(sample_test_results, 1)'
        ),
        CheckConstraint(
            'array_length(hidden_test_cases, 1) = array_length(hidden_test_results, 1)'
        ),
    )
