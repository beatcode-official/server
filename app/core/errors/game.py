from fastapi import WebSocketException


class AlreadyInGameError(WebSocketException):
    """(WebSocket) Exception raised when a user is already in a game."""

    def __init__(self):
        super().__init__(code=4000, reason="You are already in a game")


class AlreadyInQueueError(WebSocketException):
    """(WebSocket) Exception raised when a user is already in a queue."""

    def __init__(self):
        super().__init__(code=4000, reason="You are already in a queue")


class GameNotFoundError(WebSocketException):
    """(WebSocket) Exception raised when a game is not found."""

    def __init__(self):
        super().__init__(code=4004, reason="Game not found or already finished")


class PlayerNotFoundError(WebSocketException):
    """(WebSocket) Exception raised when a player is not found."""

    def __init__(self):
        super().__init__(code=4004, reason="Player not found")


class NotInThisGameError(WebSocketException):
    """(WebSocket) Exception raised when a player is not in this game."""

    def __init__(self):
        super().__init__(code=4000, reason="You're not a player in this game")
