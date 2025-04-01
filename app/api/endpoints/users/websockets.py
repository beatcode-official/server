import jwt
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from core.config import settings
from db.models.user import User
from db.session import get_db

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
    # Define an exception to raise if the credentials are invalid
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    async def close_ws_and_raise(
        code: int = 4001, reason: str = "Could not validate credentials"
    ):
        try:
            await websocket.close(code=code, reason=reason)
        except Exception:
            pass
        raise credentials_exception

    try:
        # Extract the token from the protocols header

        token = None
        for protocol in websocket.headers.get("sec-websocket-protocol", "").split(", "):
            if protocol.startswith("access_token|"):
                token = protocol.split("|")[1]
                # Accept the protocol that contains the token
                await websocket.accept(subprotocol=protocol)
                break

        if not token:
            await close_ws_and_raise()

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Extract the username and token secret from the payload
        username: str = payload.get("sub")
        token_secret: str = payload.get("secret")

        if username is None:
            await close_ws_and_raise()

    except jwt.PyJWTError:
        await close_ws_and_raise()

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        await close_ws_and_raise()

    if token_secret != user.token_secret:
        await close_ws_and_raise()

    return user
