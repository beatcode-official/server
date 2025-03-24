from typing import Optional

from fastapi import APIRouter, Depends
from schemas.game import GameView
from db.models.user import User
from api.endpoints.users import get_current_user
from services.game.manager import game_manager

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/current-game", response_model=Optional[GameView])
async def get_current_game(
    current_user: User = Depends(get_current_user),
) -> Optional[GameView]:
    """
    Check if the user is in a game and return the game state. Used for reconnection.

    :param current_user: User object
    :return: GameView object if the user is in a game, None otherwise
    """
    game_state = game_manager.get_player_game(current_user.id)
    if game_state:
        return game_manager.create_game_view(game_state, current_user.id)
    return None
