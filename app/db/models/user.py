from core.security.password import PasswordManager
from db.base_class import Base
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer,
                        String)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class User(Base):
    """
    Database model representing a user.

    :param id: The unique identifier of the user, auto-incremented.
    :param username: The username of the user, unique.
    :param email: The email of the user, unique.
    :param display_name: The display name of the user.
    :param hashed_password: The hashed password of the user.
    :param rating: The rating of the user.
    :param is_verified: Whether the user has verified their email.
    :param verification_token: The token used to verify the user's email.
    :param reset_token: The token used to reset the user's password.
    :param reset_token_expires: The expiration date of the reset token.
    :param token_secret: The secret token used to immediately revoke access when events like password changes happen. 
    :param created_at: The epoch time when the user was created.
    :param updated_at: The epoch time when the user was last updated.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    rating = Column(Float, default=0)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, nullable=True)
    reset_token = Column(String, unique=True, nullable=True)
    reset_token_expires = Column(Float, nullable=True)
    token_secret = Column(String, nullable=True, server_default=PasswordManager.generate_secret_token())
    created_at = Column(Float, server_default=func.extract('epoch', func.now()))
    updated_at = Column(Float, server_default=func.extract('epoch', func.now()))


class RefreshToken(Base):
    """
    Database model representing a refresh token.

    :param id: The unique identifier of the refresh token, auto-incremented.
    :param token: The refresh token, unique.
    :param user_id: The unique identifier of the user.
    :param expires_at: The expiration date and time of the refresh token.
    :param created_at: The epoch time the refresh token was created.
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(Float, nullable=False)
    created_at = Column(Float, server_default=func.extract('epoch', func.now()))

    # Relationship allows for querying the user associated with the refresh token or vice versa.
    user = relationship("User", backref="refresh_tokens")
