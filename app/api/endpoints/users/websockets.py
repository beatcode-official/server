from core.config import settings
from core.errors.auth import (
    WSExpiredTokenError,
    WSInvalidTokenError,
    WSUserNotFoundError,
)
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket
import jwt
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


async def get_current_user_ws(
    websocket: WebSocket, db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current user from the JWT token in a WebSocket connection.
    In addition to sending the 401 status code, this dependency also closes the WebSocket connection.

    :param websocket: The WebSocket connection
    :param db: The database session
    """
    token = None
    payload = None
    username = None
    token_secret = None

    try:
        # Extract the token from the protocols header
        for protocol in websocket.headers.get("sec-websocket-protocol", "").split(", "):
            if protocol.startswith("access_token|"):
                token = protocol.split("|")[1]
                await websocket.accept(subprotocol=protocol)
                break

        if not token:
            raise WSInvalidTokenError()

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise WSExpiredTokenError()
        except jwt.InvalidTokenError:  # Catch broader invalid token errors
            raise WSInvalidTokenError()
        except jwt.PyJWTError:
            raise WSInvalidTokenError()

        if payload is None:
            raise WSInvalidTokenError()

        username = payload.get("sub")
        token_secret = payload.get("secret")

        if username is None:
            raise WSUserNotFoundError()
    except jwt.PyJWTError:
        raise WSInvalidTokenError()

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise WSUserNotFoundError()

    if token_secret != user.token_secret:
        raise WSInvalidTokenError()

    return user
