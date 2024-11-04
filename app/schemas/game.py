from typing import Dict, Optional

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
    """
    match_id: str
    opponent_name: str
    opponent_display_name: str
    current_problem_index: int
    problems_solved: int
    opponent_problems_solved: int
    your_hp: int
    opponent_hp: int
    match_type: str
    start_time: float
    status: str
    winner: Optional[str] = None


class MatchResult(BaseModel):
    """
    A model for the result of a match.

    :param winner_username: The username of the winner.
    :param player1_username: The username of player 1.
    :param player2_username: The username of player 2.
    :param player1_hp: The HP of player 1.
    :param player2_hp: The HP of player 2.
    :param player1_problems_solved: The number of problems solved by player 1.
    :param player2_problems_solved: The number of problems solved by player 2.
    :param player1_partial_progress: The partial progress of player 1.
    :param player2_partial_progress: The partial progress of player 2.
    :param match_type: The type of the match.
    :param rating_changes: The dict mapping rating changes of the players.
    """
    winner_username: Optional[str]
    player1_username: str
    player2_username: str
    player1_hp: int
    player2_hp: int
    player1_problems_solved: int
    player2_problems_solved: int
    player1_partial_progress: Dict[int, int]
    player2_partial_progress: Dict[int, int]
    match_type: str
    rating_changes: Optional[Dict[str, float]] = None


class GameEvent(BaseModel):
    """
    Simple model for a game event.

    :param type: The type of the event.
    :param data: The data of the event.
    """
    type: str
    data: Dict
