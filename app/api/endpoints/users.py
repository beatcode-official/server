import time
from typing import Annotated

from core.config import settings
from core.security.jwt import jwt_manager
from core.security.password import PasswordManager
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from schemas.user import (ForgotPassword, PasswordReset, Token, TokenRefresh,
                          UserCreate, UserResponse, UserUpdate)
from services.email.service import email_service
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/users", tags=["users"])
oath2_scheme = OAuth2PasswordBearer(tokenUrl=f"api/users/login")


async def get_current_user(
    token: Annotated[str, Depends(oath2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current user from the JWT token

    :param token: The JWT token
    :param db: The database session
    """
    # Define an exception to raise if the credentials are invalid
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Extract the username and token secret from the payload
        username: str = payload.get("sub")
        token_secret: str = payload.get("secret")

        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    # Check if the token secret in the payload matches the user's token secret
    if token_secret != user.token_secret:
        raise credentials_exception

    return user


async def get_current_user_ws(
    websocket: WebSocket,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current user from the JWT token in a WebSocket connection.
    In addition to sending the 401 status code, this dependency also closes the WebSocket connection.

    :param websocket: The WebSocket connection
    :param db: The database session
    """
    # Define an exception to raise if the credentials are invalid
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )

    async def close_ws_and_raise(
        code: int = 4001,
        reason: str = "Could not validate credentials"
    ):
        await websocket.close(code=code, reason=reason)
        raise credentials_exception

    try:
        # Extract the token from the authorization header
        auth_header = websocket.headers.get("authorization", "")

        # Quick and dirty check for the Bearer token
        if not auth_header.startswith("Bearer "):
            await close_ws_and_raise()

        token = auth_header.split(" ")[1]
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Extract the username and token secret from the payload
        username: str = payload.get("sub")
        token_secret: str = payload.get("secret")

        if username is None:
            await close_ws_and_raise()

    except JWTError:
        await close_ws_and_raise()

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        await close_ws_and_raise()

    if token_secret != user.token_secret:
        await close_ws_and_raise()

    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    # Check for existing username or email first
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        # Generate verification token - make it unique even in test mode
        if settings.TESTING:
            # Add timestamp to make it unique
            import time
            verification_token = f"{settings.TEST_EMAIL_TOKEN}_{int(time.time())}"
        else:
            verification_token = PasswordManager.generate_secret_token()
            email_service.send_verification_email(user.email, verification_token)

        # Generate token secret
        token_secret = PasswordManager.generate_secret_token()

        # Create the user
        db_user = User(
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            hashed_password=PasswordManager.hash_password(user.password),
            verification_token=verification_token,
            token_secret=token_secret
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    except IntegrityError as e:
        db.rollback()
        print(f"Database IntegrityError: {str(e)}")  # Log the error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed: User already exists"
        )
    except Exception as e:
        db.rollback()
        print(f"Unexpected error during registration: {str(e)}")  # Log the error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify a user's email.

    :param token: The verification token
    :param db: The database session
    """
    # Query the database for the user with the verification token
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    forgot_pwd: ForgotPassword,
    db: Session = Depends(get_db)
):
    """
    Send a password reset email.

    :param forgot_pwd: The email to send the password reset link to
    :param db: The database session
    """
    # Query the database for the user with the email
    user = db.query(User).filter(User.email == forgot_pwd.email).first()

    # Same message to avoid leaking information
    if not user:
        return {
            "message": "If the email exists, a password reset link will be sent"
        }

    # Generate and store the reset token, and send the email
    reset_token = PasswordManager.generate_secret_token()
    if settings.TESTING:
        reset_token = settings.TEST_EMAIL_TOKEN
    else:
        reset_token = PasswordManager.generate_secret_token()
        email_service.send_password_reset_email(user.email, reset_token)

    user.reset_token = reset_token
    user.reset_token_expires = time.time() + settings.PASSWORD_RESET_TOKEN_EXPIRE * 60

    db.commit()

    return {"message": "If the email exists, a password reset link will be sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset a user's password.

    :param reset_data: The reset data (containing the reset token and new password)
    :param db: The database session
    """
    # Query the database for the user with the reset token
    user = db.query(User).filter(User.reset_token == reset_data.token).first()

    # Check if the user exists and the reset token is valid
    if not user or not user.reset_token_expires or user.reset_token_expires < time.time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Reset the password and clear the reset token
    user.hashed_password = PasswordManager.hash_password(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expires = None

    # Generate a new token secret to invalidate all existing tokens
    user.token_secret = PasswordManager.generate_secret_token()

    # Invalidate all existing refresh tokens
    jwt_manager.revoke_all_refresh_tokens(user.id, db)

    db.commit()

    return {"message": "Password reset successful"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get the current user.

    :param current_user: The current user
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Update the current user.

    :param user_update: The updated user data
    :param current_user: The current user
    :param db: The database session
    """
    # Update the user fields specified in the user update dictionary
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)  # Refresh the user to get the user's updated fields

    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Delete the current user.

    :param current_user: The current user
    :param db: The database session
    """
    db.delete(current_user)
    db.commit()
    return {
        "message": "User deleted successfully"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh the user's access and refresh tokens.

    :param token_data: The token data (containing the refresh token)
    :param db: The database session
    """
    # Verify the refresh token
    user = jwt_manager.verify_refresh_token(token_data.refresh_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Revoke the refresh token and create new tokens
    jwt_manager.revoke_refresh_token(token_data.refresh_token, db)
    access_token, refresh_token = jwt_manager.create_tokens(user, db)

    # Cleanup expired refresh tokens
    jwt_manager.cleanup_refresh_tokens(user.id, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.username == form_data.username) |
        (User.email == form_data.username)
    ).first()

    if not user or not PasswordManager.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials"
        )

    # Generate tokens
    access_token, refresh_token = jwt_manager.create_tokens(user, db)
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Log out the user by revoking their provided refresh token.

    :param token_data: The token data (containing the refresh token)
    :param current_user: The current user
    :param db: The database session
    """
    jwt_manager.revoke_refresh_token(token_data.refresh_token, db)
    jwt_manager.cleanup_refresh_tokens(current_user.id, db)
    return {"message": "Succesfully logged out"}
