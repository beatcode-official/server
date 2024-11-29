from datetime import date
from pydantic import BaseModel


class Token(BaseModel):
    """
    The JWT token is used to authenticate users
    It contains 3 parts:
    - Header: Contains the type of token and the hashing algorithm used
    - Payload: Contains the claims. Claims are statements about an entity (typically, the user) and additional data.
    - Signature: Contains the signature of the token that can be used to verify that the sender of the JWT is who it says it is and to ensure that the message wasn't changed along the way.

    Below is the definition of the Token class, which is used to handle auth
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Store data of the username after extracting it from the JWT token (decoding it)
    """

    username: str | None = None


class User(BaseModel):
    """
    defining template for the request body for the user data endpoints

    """

    username: str
    display_name: str
    email: str | None = None
    date_joined: date
    disabled: bool | None = None


# inherit from User class to add password field
class UserInDB(User):
    """
    We don't want to expose hashed_password to the client side, so we create a new class UserInDB that inherits from User and adds hashed_password field
    """

    password: str


# Defining template for the request body for the create-room and join-room endpoints - @HuyNgo
class PlayerJoin(BaseModel):
    player_name: str
