import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional

from core.config import settings
from db.models.problem import Problem
from fastapi import WebSocket
from pydantic import BaseModel
from schemas.game import GameEvent


class GameStatus(str, Enum):
    """
    Enum for the status of a game, useful for preventing typos.
    """
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class PlayerState(BaseModel):
    """
    A model representing the state of a player in a game.

    :param user_id: The ID of the user.
    :param username: The username of the user.
    :param display_name: The display name of the user.
    :param current_problem_index: The index of the current problem the player is working on [0-MATCH_PROBLEM_COUNT)
    :param hp: The health points of the player.
    :param problems_solved: The number of problems the player has solved.
    :param partial_progress: A dictionary mapping problem indices to the number of test cases passed.
    :param last_submission: The timestamp of the last submission.
    :param ws: The WebSocket connection of the player.

    """
    user_id: int
    username: str
    display_name: str
    current_problem_index: int = 0
    hp: int = settings.STARTING_HP if not settings.TESTING else 140
    problems_solved: int = 0
    partial_progress: Dict[int, int] = {}
    last_submission: Optional[float] = None
    ws: Optional[WebSocket] = None
    skill_points: int = settings.STARTING_SP
    mana_points: int = settings.STARTING_MP
    abilities: List[str] = []

    # Necessary for inclusion of types like WebSocket
    class Config:
        arbitrary_types_allowed = True

    async def send_event(self, event: GameEvent):
        """
        Sends a game event to the player's websocket.
        """
        if self.ws:
            try:
                model_dict = event.model_dump()
                await self.ws.send_json(model_dict)
                return True
            except Exception:
                self.ws = None
                return False
        return False


class GameState(BaseModel):
    """
    A model representing the state of a game.

    :param id: The ID of the game.
    :param status: The status of the game.
    :param player1: The state of player 1.
    :param player2: The state of player 2.
    :param problems: The list of problems in the match.
    :param start_time: The timestamp of the start of the game.
    :param match_type: The type of the match.
    :param winner: The ID of the winner of the game.
    :param is_cleaning_up: A flag indicating whether the game is cleaning up.
    """
    id: str
    status: GameStatus
    player1: PlayerState
    player2: PlayerState
    problems: List[Problem]
    start_time: float
    match_type: str
    winner: Optional[str] = None
    is_cleaning_up: bool = False
    timeout_task: Optional[asyncio.Task] = None
    player1_rating_change: Optional[float] = None
    player2_rating_change: Optional[float] = None
    custom_settings: Optional[Dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def broadcast_event(self, event: GameEvent):
        """
        Broadcasts a game event to both players.

        :param event: The game event to broadcast.
        """
        await self.player1.send_event(event)
        await self.player2.send_event(event)

    def get_player_state(self, player_id: int) -> Optional[PlayerState]:
        """
        Gets the state of a player given their ID.

        :param player_id: The ID of the player.
        :return: The state of the player if found, otherwise None.
        """
        if self.player1.user_id == player_id:
            return self.player1
        if self.player2.user_id == player_id:
            return self.player2
        return None

    def get_opponent_state(self, player_id: int) -> Optional[PlayerState]:
        """
        Gets the state of the opponent of a player given their ID.

        :param player_id: The ID of the player.
        :return: The state of the opponent if found, otherwise None.
        """
        if self.player1.user_id == player_id:
            return self.player2
        if self.player2.user_id == player_id:
            return self.player1
        return None

    def is_timed_out(self) -> bool:
        """
        Check if the match has timed out.

        :return: True if the match has timed out, False otherwise.
        """
        elapsed_time = time.time() - self.start_time
        timeout = settings.MATCH_TIMEOUT_MINUTES * 60 if not settings.TESTING else 3 * 60  # change when testing (timeout test = 20, normal = 3 * 60)
        return elapsed_time >= timeout
