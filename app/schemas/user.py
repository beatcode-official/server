from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UsernameStr = Annotated[str, Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_-]+$")]
DisplayNameStr = Annotated[str, Field(min_length=1, max_length=50)]
PasswordStr = Annotated[str, Field(min_length=6)]


class UserBase(BaseModel):
    username: UsernameStr
    email: EmailStr
    display_name: DisplayNameStr


class UserCreate(UserBase):
    password: PasswordStr


class UserUpdate(BaseModel):
    display_name: Optional[DisplayNameStr] = None


class UserLogin(BaseModel):
    login: str
    password: PasswordStr


class PasswordReset(BaseModel):
    token: str
    new_password: PasswordStr


class ForgotPassword(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    username: UsernameStr
    email: EmailStr
    display_name: DisplayNameStr
    rating: float
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
