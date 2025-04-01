import random
import string
import time
from typing import Annotated

from core.config import settings
from core.security.jwt import jwt_manager
from core.security.password import PasswordManager
from db.models.user import RefreshToken, User
from db.models.game import Match
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from schemas.user import (
    ForgotPassword,
    PasswordReset,
    Token,
    TokenRefresh,
    UserCreate,
    UserCreateWithGoogle,
    UserResponse,
    UserUpdate,
)
from services.email.service import email_service
from sqlalchemy.orm import Session
import jwt
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

router = APIRouter(prefix="/users", tags=["users"])
oath2_scheme = OAuth2PasswordBearer(tokenUrl=f"users/login")


async def get_current_user(
    token: Annotated[str, Depends(oath2_scheme)], db: Session = Depends(get_db)
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
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Extract the username and token secret from the payload
        username: str = payload.get("sub")
        token_secret: str = payload.get("secret")

        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    # Check if the token secret in the payload matches the user's token secret
    if token_secret != user.token_secret:
        raise credentials_exception

    return user

@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    :param user: The user data
    :param db: The database session

    :raises HTTPException: If the username or email already exists

    :return: The created user
    """
    # Check for existing username or email
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Send verification email
    if settings.TESTING:
        verification_token = settings.TEST_EMAIL_TOKEN
    else:
        verification_token = PasswordManager.generate_secret_token()
        email_service.send_verification_email(user.email, verification_token)

    # Create the user
    db_user = User(
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        hashed_password=PasswordManager.hash_password(user.password),
        verification_token=verification_token,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Refresh the user to get the user's updated fields

    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Log in a user.

    :param form_data: The login form data
    :param db: The database session

    :raises HTTPException: If the login credentials are incorrect or the email is not verified

    :return: The user's access and refresh tokens
    """
    # Query the database for the user with the username or email
    user = (
        db.query(User)
        .filter(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
        .first()
    )

    # Check if the user exists and the password is correct
    if not user or not PasswordManager.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if the email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    access_token, refresh_token = jwt_manager.create_tokens(user, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(forgot_pwd: ForgotPassword, db: Session = Depends(get_db)):
    """
    Send a password reset email.

    :param forgot_pwd: The email to send the password reset link to
    :param db: The database session
    """
    # Query the database for the user with the email
    user = db.query(User).filter(User.email == forgot_pwd.email).first()

    # Same message to avoid leaking information
    if not user:
        return {"message": "If the email exists, a password reset link will be sent"}

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
async def reset_password(reset_data: PasswordReset, db: Session = Depends(get_db)):
    """
    Reset a user's password.

    :param reset_data: The reset data (containing the reset token and new password)
    :param db: The database session
    """
    # Query the database for the user with the reset token
    user = db.query(User).filter(User.reset_token == reset_data.token).first()

    # Check if the user exists and the reset token is valid
    if (
        not user
        or not user.reset_token_expires
        or user.reset_token_expires < time.time()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
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
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get the current user.

    :param current_user: The current user
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Update the current user.

    :param user_update: The updated user data
    :param current_user: The current user
    :param db: The database session
    """
    # Prevent guests from updating their display name
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest users cannot change their account details",
        )

    # Update the user fields specified in the user update dictionary
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)  # Refresh the user to get the user's updated fields

    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """
    Delete the current user.

    :param current_user: The current user
    :param db: The database session
    """
    db.delete(current_user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
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
            detail="Invalid or expired refresh token",
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


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
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


@router.post("/guest", response_model=Token)
async def create_guest_account(db: Session = Depends(get_db)):
    """
    Create a guest account and return access tokens

    :param db: The database session
    :return: The guest's access and refresh tokens
    """
    try:
        # Clean up old guest accounts and their refresh tokens first
        time_limit = time.time() - (2 * 60 * 60)  # 2 hours ago

        # First delete associated refresh tokens
        old_guest_users = (
            db.query(User)
            .filter(User.is_guest == True, User.created_at < time_limit)
            .all()
        )

        # Delete all records of old guest users to prevent foreign key violations
        for user in old_guest_users:
            db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
            db.query(Match).filter(Match.player1_id == user.id).delete()
            db.query(Match).filter(Match.player2_id == user.id).delete()

        # Then delete the guest users
        db.query(User).filter(
            User.is_guest == True, User.created_at < time_limit
        ).delete()

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up guest accounts: {e}")

    # Generate guest credentials
    random_string = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=10)
    )
    username = f"guest_{random_string}"
    display_name = f"Guest_{random_string[:5]}"
    email = f"{random_string}-not-an-actual@email.com"
    password = PasswordManager.generate_secret_token()

    # Create the guest account
    db_user = User(
        username=username,
        email=email,
        display_name=display_name,
        hashed_password=PasswordManager.hash_password(password),
        is_verified=True,
        is_guest=True,
        token_secret=PasswordManager.generate_secret_token(),
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating guest account",
        )

    # Generate tokens
    access_token, refresh_token = jwt_manager.create_tokens(db_user, db)
    return {"access_token": access_token, "refresh_token": refresh_token}


def create_google_flow(state=None):
    """
    Create a Google OAuth flow object.

    :return: The Google OAuth flow object
    """
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://accounts.google.com/o/oauth2/token",
            }
        },
        scopes=settings.GOOGLE_CLIENT_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
    )


@router.get("/google/redirect")
async def google_redirect():
    """
    Redirect user to Google's OAuth authorization page.
    """
    flow = create_google_flow()
    url, _ = flow.authorization_url()
    return {"url": url}


@router.post("/google/login")
async def google_login(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Login function for Google OAuth

    Google redirects back with `code`. Server exchanges code for token, fetches user profile, logs user in or registers them.

    :return: Access and refresh tokens if user exists, else user data for registration
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No code found"
        )

    flow = create_google_flow(state=state)

    # Exchange code for tokens and retrieve user info
    flow.fetch_token(code=code)
    credentials = flow.credentials
    oauth2_client = build("oauth2", "v2", credentials=credentials)
    user_info = oauth2_client.userinfo().get().execute()

    # Extract relevant fields
    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name")
    avatar_url = user_info.get("picture")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing account information from Google",
        )

    # See if user already exists
    db_user = db.query(User).filter(User.google_id == google_id).first()
    if not db_user:
        # Create user account if not
        existing_user_by_email = db.query(User).filter(User.email == email).first()
        if existing_user_by_email:
            # Possibly link that user’s google_id so next time it matches
            existing_user_by_email.google_id = google_id
            db.add(existing_user_by_email)
            db.commit()
            db.refresh(existing_user_by_email)
            db_user = existing_user_by_email
        else:
            return {
                "google_id": google_id,
                "email": email,
                "name": name,
                "avatar_url": avatar_url,
            }

    access_token, refresh_token = jwt_manager.create_tokens(db_user, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/google/register")
async def google_register(
    user: UserCreateWithGoogle, db: Session = Depends(get_db)
) -> dict:
    """
    Register a new user with Google OAuth.

    :param user: The user data
    :param db: The database session

    :raises HTTPException: If the username or email already exists

    :return: Access and refresh tokens
    """
    # Check for existing username or email
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create the user
    db_user = User(
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        hashed_password="",
        google_id=user.google_id,
        avatar_url=user.avatar_url,
        is_verified=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token, refresh_token = jwt_manager.create_tokens(db_user, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
