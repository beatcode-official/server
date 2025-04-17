from fastapi import HTTPException, WebSocketException, status


class CredentialError(HTTPException):
    """Exception raised when credentials cannot be validated."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class WSInvalidTokenError(WebSocketException):
    """(WebSocket) Exception raised when token is invalid when connecting to the websocket"""

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(code=4001, reason=detail)


class WSExpiredTokenError(WebSocketException):
    """(WebSocket) Exception raised when token is expired"""

    def __init__(self, detail: str = "Expired token"):
        super().__init__(code=4001, reason=detail)


class WSUserNotFoundError(WebSocketException):
    """(WebSocket) Exception raised when user is not found"""

    def __init__(self, detail: str = "User not found"):
        super().__init__(code=4004, reason=detail)
