from fastapi import HTTPException, status


class SubmittingTooFastError(Exception):
    """Exception raised when a user submits too fast."""

    def __init__(self, remaining_cooldown):
        self.remaining_cooldown = remaining_cooldown
        self.message = f"You're submitting too fast. Please wait {self.remaining_cooldown:.2f} seconds before submitting again."
        super().__init__(self.message)


class AlreadyInGameError(HTTPException):
    """Exception raised when a user is already in a game."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, detail="You are already in a game."
        )
