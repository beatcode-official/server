from fastapi import WebSocket, HTTPException, WebSocketException, status
from typing import Optional


class RoomNotFoundError(HTTPException):
    """Exception raised when a room is not found."""

    def __init__(self):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


class RoomFullError(HTTPException):
    """Exception raised when a room is full."""

    def __init__(self):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail="Room is full")


class AlreadyInRoomError(HTTPException):
    """Exception raised when a user is already in a room."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already in a room"
        )


class GuestUpdateSettingsError(HTTPException):
    """Exception raised when a guest tries to update room settings."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can update room settings",
        )


class WSRoomNotFoundError(WebSocketException):
    """(WebSocket) Exception raised when a room is not found."""

    def __init__(self):
        super().__init__(code=4004, reason="Room not found")


class WSRoomFullError(WebSocketException):
    """(WebSocket) Exception raised when a room is full."""

    def __init__(self):
        super().__init__(code=4003, reason="Room is full")


class WSAlreadyInRoomError(WebSocketException):
    """(WebSocket) Exception raised when a user is already in another room."""

    def __init__(self):
        super().__init__(code=4000, reason="Already in another room")


class WSGameInProgressError(WebSocketException):
    """(WebSocket) Exception raised when a game is in progress."""

    def __init__(self):
        super().__init__(
            code=4000, reason="Cannot modify room settings while game is in progress"
        )


class RoomError(Exception):
    def __init__(self, message: str):
        self.message = message

    async def send_json(self, websocket: WebSocket):
        await websocket.send_json({"type": "error", "data": {"message": self.message}})


class GuestStartGameError(RoomError):
    """Send error message when a guest tries to start a game."""

    def __init__(self):
        super().__init__(message="Only the host can start the game")


class NotAllPlayersReadyError(RoomError):
    """Send error message when one player is not ready to start."""

    def __init__(self):
        super().__init__(message="All players must be ready to start")


class NotEnoughPlayersError(RoomError):
    """Send error message when there are not enough players to start."""

    def __init__(self):
        super().__init__(message="Need 2 players to start")
