from typing import Dict, List, Optional

from pydantic import BaseModel


class GameView(BaseModel):
    """
    A model for a user's view of a game.

    :param match_id: The match ID.
    :param opponent_name: The opponent's username.
    :param opponent_display_name: The opponent's display name.
    :param current_problem_index: The index of the current problem.
    :param problems_solved: The number of problems solved by the user.
    :param opponent_problems_solved: The number of problems solved by the opponent.
    :param your_hp: The user's HP.
    :param opponent_hp: The opponent's HP.
    :param match_type: The type of the match.
    :param start_time: The start time of the match (epoch)
    :param status: The status of the match.
    :param winner: The winner of the match.
    :param rating_change: The rating change of the user.
    """

    match_id: str
    opponent_name: str
    opponent_display_name: str
    opponent_avatar_url: Optional[str] = None
    current_problem_index: int
    problems_solved: int
    opponent_problems_solved: int
    your_hp: int
    opponent_hp: int
    match_type: str
    start_time: float
    status: str
    winner: Optional[str] = None
    rating_change: Optional[float] = None
    skill_points: int
    mana_points: int
    abilities: List[str]


class GameEvent(BaseModel):
    """
    Simple model for a game event.

    :param type: The type of the event.
    :param data: The data of the event.
    """

    type: str
    data: Dict
