import secrets

import bcrypt


class PasswordManager:
    """
    A static class to manage password hashing and verification.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        :param password: The password to hash.
        :return: The hashed password
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hashed password.

        :param plain_password: The plain text password.
        :param hashed_password: The hashed password.

        :return: Whether the password is correct.
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    @staticmethod
    def generate_secret_token() -> str:
        """
        Generate a random secret token.

        :return: The generated secret token.
        """
        return secrets.token_urlsafe(64)
