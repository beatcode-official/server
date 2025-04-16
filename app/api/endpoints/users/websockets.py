from core.config import settings
from core.errors.auth import CredentialError
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
    # Define an exception to raise if the credentials are invalid
    # credentials_exception = HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     detail="Could not validate credentials",
    # )

    # Initialize variables at function scope to avoid UnboundLocalError
    token = None
    payload = None
    username = None
    token_secret = None

    try:
        # Extract the token from the protocols header

        # import pdb; pdb.set_trace()  # Comment out debugger
        for protocol in websocket.headers.get("sec-websocket-protocol", "").split(", "):
            if protocol.startswith("access_token|"):
                token = protocol.split("|")[1]
                # Accept the protocol that contains the token
                await websocket.accept(subprotocol=protocol)
                break

        if not token:
            raise CredentialError()

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise CredentialError()
        except jwt.InvalidTokenError:  # Catch broader invalid token errors
            raise CredentialError()
        except jwt.PyJWTError:
            raise CredentialError()

        if payload is None:
            raise CredentialError()

        username = payload.get("sub")
        token_secret = payload.get("secret")

        if username is None:
            raise CredentialError()
    except jwt.PyJWTError:
        raise CredentialError()

    # Query the database for the user with that username
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise CredentialError()

    if token_secret != user.token_secret:
        raise CredentialError()

    return user
