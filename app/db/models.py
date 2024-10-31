from db.base import Base
from services.email import generate_token
from sqlalchemy import (JSON, Boolean, Column, DateTime, Float, Integer,
                        String, Text)
from sqlalchemy.sql import func


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


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)  # HTML Format
    difficulty = Column(String, nullable=False, index=True)
    sample_test_cases = Column(JSON, nullable=False)
    sample_test_results = Column(JSON, nullable=False)
    hidden_test_cases = Column(JSON, nullable=False)
    hidden_test_results = Column(JSON, nullable=False)
    boilerplate = Column(Text, nullable=False)
    compare_func = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
