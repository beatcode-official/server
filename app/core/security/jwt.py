import time
from typing import Optional, Tuple

from core.config import settings
from core.security.password import PasswordManager
from db.models.user import RefreshToken, User
from jose import jwt
from sqlalchemy.orm import Session


class JWTManager:
    """
    A class to manage JWT and refresh tokens.
    """

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        data: dict,
        user: Optional[User] = None,
        expires_delta: Optional[int] = None
    ) -> str:
        """
        Create an access token with the given data.

        :param data: The data to encode in the token.
        :param user: The user to encode in the token.
        :param expires_delta: The number of seconds until the token expires.

        :return: The encoded access token.
        """
        # Shallow copy the data to avoid modifying the original data.
        to_encode = data.copy()

        # If expiration time is not explicitly provided, set it to setting's default value.
        if expires_delta:
            expire = time.time() + expires_delta
        else:
            expire = time.time() + self.access_token_expire_minutes * 60

        # Add the expiration time and the user's secret to the token.
        to_encode.update({
            "exp": expire,
            "secret": user.token_secret if user else None
        })

        # Return the encoded token.
        return jwt.encode(
            to_encode,
            key=self.secret_key,
            algorithm=self.algorithm
        )

    def create_tokens(
        self,
        user: User,
        db: Session
    ) -> Tuple[str, str]:
        """
        Create an access token and a refresh token for the given user.

        :param user: The user to create the tokens for.
        :param db: The database session to use.

        :return: A tuple containing the access token and the refresh token.
        """
        # Create an access token for the user.
        access_token = self.create_access_token(
            data={"sub": user.username},
            user=user,
            expires_delta=self.access_token_expire_minutes * 60
        )

        # Create a refresh token for the user and save it to the database.
        refresh_token = PasswordManager.generate_secret_token()
        expires_at = time.time() + self.refresh_token_expire_days * 24 * 60 * 60

        db_token = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            expires_at=expires_at
        )

        db.add(db_token)
        db.commit()

        # Return the access token and the refresh token.
        return access_token, refresh_token

    def verify_refresh_token(
        self,
        token: str,
        db: Session
    ) -> Optional[User]:
        """
        Verify the given refresh token and return the associated user.

        :param token: The refresh token to verify.
        :param db: The database session to use.

        :return: The user associated with the refresh token, or None if the token is invalid.
        """
        # Query for a token that matches the given token and is not expired.
        db_token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == token,
                RefreshToken.expires_at > time.time(),
            ).first()
        )

        if db_token:
            return db_token.user

        return None

    def revoke_refresh_token(
        self,
        token: str,
        db: Session
    ):
        """
        Revoke the given refresh token.

        :param token: The refresh token to revoke.
        :param db: The database session to use.
        """
        # Query for a token that matches the given token and delete it.
        db.query(RefreshToken).filter(
            RefreshToken.token == token
        ).delete()

        db.commit()

    def revoke_all_refresh_tokens(self, user_id: int, db: Session):
        """
        Revoke all refresh tokens for the given user.

        :param user_id: The ID of the user to revoke refresh tokens for.
        :param db: The database session to use.
        """
        # Delete all refresh tokens that match the given user ID.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id
        ).delete()

        db.commit()

    def cleanup_refresh_tokens(self, user_id: int, db: Session):
        """
        Cleanup expired refresh tokens for the given user.

        :param user_id: The ID of the user to cleanup refresh tokens for.
        :param db: The database session to use.
        """
        # Delete all refresh tokens that are expired.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at < time.time()
        ).delete()

        db.commit()
