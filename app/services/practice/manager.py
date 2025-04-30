from typing import Optional

from schemas.game import GameView
from services.game.manager import GameManager
from services.game.state import GameState


class PracticeGameManager(GameManager):
    """
    A service class for managing practice game state and operations.

    This is a simplified version of the GameManager class that only includes
    the functionality needed for practice mode.
    """

    def __init__(self):
        super().__init__()

    def create_game_view(self, game_state: GameState, user_id: int) -> GameView:
        """
        Create a GameView object from a GameState object.

        :param game_state: GameState object
        :param user_id: ID of the user requesting the view
        :return: A GameView object representing the game state for the user
        """
        game_view = super().create_game_view(game_state, user_id)
        game_view.rating_change = None
        is_player1 = game_state.player1.user_id == user_id
        opponent = game_state.player2 if is_player1 else game_state.player1
        game_view.opponent_name = opponent.username
        game_view.opponent_display_name = opponent.display_name
        game_view.opponent_rating = opponent.rating
        game_view.opponent_avatar_url = opponent.avatar_url
        return game_view

    async def get_winner(self, game: GameState) -> Optional[str]:
        """
        Determines the winner of a GameState.

        :param game: The game state object.
        :return: The username of the winner, or None if it is a draw.
        """
        if game.player1.hp < game.player2.hp:
            return game.player2.username
        elif game.player2.hp < game.player1.hp:
            return game.player1.username
        else:
            return None


practice_game_manager = PracticeGameManager()
