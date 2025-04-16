from fastapi import HTTPException, status


class CredentialError(HTTPException):
    """Exception raised when credentials cannot be validated."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
