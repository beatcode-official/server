from typing import Annotated, Optional

from core.config import settings
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Custom Pydantic types with validation
UsernameStr = Annotated[
    str,
    Field(
        min_length=settings.USERNAME_MIN_LENGTH,
        max_length=settings.USERNAME_MAX_LENGTH,
        pattern=settings.USERNAME_REGEX)
]
DisplayNameStr = Annotated[
    str,
    Field(
        min_length=settings.DISPLAY_NAME_MIN_LENGTH,
        max_length=settings.DISPLAY_NAME_MAX_LENGTH,
        pattern=settings.DISPLAY_NAME_REGEX
    )
]
PasswordStr = Annotated[
    str,
    Field(
        min_length=settings.PASSWORD_MIN_LENGTH
    )
]


class UserBase(BaseModel):
    """
    Base schema for user data.
    """
    username: UsernameStr
    email: EmailStr
    display_name: DisplayNameStr


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """
    password: PasswordStr


class UserUpdate(BaseModel):
    """
    Schema for updating user data.
    """
    display_name: Optional[DisplayNameStr] = None


class UserResponse(BaseModel):
    """
    A response schema to return user data to the client.
    """
    username: UsernameStr
    email: EmailStr
    display_name: DisplayNameStr
    rating: float
    is_verified: bool
    created_at: float
    updated_at: Optional[float] = None

    # Allow reading data from the model's attributes
    model_config = ConfigDict(from_attributes=True)


class ForgotPassword(BaseModel):
    """
    A schema for requesting a password reset.
    """
    email: EmailStr


class PasswordReset(BaseModel):
    """
    A schema for resetting the password.
    """
    token: str
    new_password: PasswordStr


class Token(BaseModel):
    """
    A schema for returning the access token.
    """
    access_token: str
    refresh_token: str


class TokenRefresh(BaseModel):
    """
    A schema for refreshing the access token.
    """
    refresh_token: str
