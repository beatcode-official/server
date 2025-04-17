import asyncio
from typing import Any, Dict, Optional

from schemas.game import GameView
from services.game.ability import ability_manager
from services.game.manager import GameManager
from services.game.state import GameState


class PracticeGameManager(GameManager):
    """
    A service class for managing practice game state and operations.

    This is a simplified version of the GameManager class that only includes
    the functionality needed for practice mode.
    """

    def __init__(self):
        self.active_games: Dict[str, GameState] = {}
        self.player_to_game: Dict[int, str] = {}  # Maps player ID to game ID
        self.timeout_tasks: Dict[str, asyncio.Task] = {}

    def create_game_view(self, game_state: GameState, user_id: int) -> GameView:
        """
        Create a GameView object from a GameState object.

        :param game_state: GameState object
        :param user_id: ID of the user requesting the view
        :return: A GameView object representing the game state for the user
        """
        is_player1 = game_state.player1.user_id == user_id
        player = game_state.player1 if is_player1 else game_state.player2
        opponent = game_state.player2 if is_player1 else game_state.player1

        return GameView(
            match_id=game_state.id,
            opponent_name=opponent.username,
            opponent_display_name=opponent.display_name,
            opponent_rating=opponent.rating,
            opponent_avatar_url=opponent.avatar_url,
            current_problem_index=player.current_problem_index,
            problems_solved=player.problems_solved,
            opponent_problems_solved=opponent.problems_solved,
            your_hp=player.hp,
            opponent_hp=opponent.hp,
            match_type=game_state.match_type,
            start_time=game_state.start_time,
            status=game_state.status.value,
            winner=game_state.winner,
            rating_change=None,
            skill_points=player.skill_points,
            mana_points=player.mana_points,
            abilities=player.abilities,
        )

    async def handle_ability_message(
        self,
        game_state: GameState,
        _: Any,
        player_id: int,
        message: Dict,
    ) -> Optional[str]:
        """
        Handle ability messages in practice mode.

        :param game_state: The current game state
        :param _: Unused parameter (for compatibility with game.manager)
        :param player_id: The id of the player sending the message
        :param message: The ability message
        :return: Error message if any
        """
        # Forward the message to the ability manager but use ourselves as the game_manager
        return await ability_manager.handle_ability_message(
            game_state, self, player_id, message
        )

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

    def register_game(self, game_state: GameState) -> None:
        """
        Registers a game with the manager.

        :param game_state: The game state to register
        """
        self.active_games[game_state.id] = game_state
        self.player_to_game[game_state.player1.user_id] = game_state.id
        self.player_to_game[game_state.player2.user_id] = game_state.id

    async def cleanup_game(self, game_id: str) -> None:
        """
        Cleans up a game after it has ended.

        :param game_id: The ID of the game.
        """
        # Remove the game from the active games and player to game mappings
        game = self.active_games.pop(game_id, None)
        if game:
            self.player_to_game.pop(game.player1.user_id, None)
            self.player_to_game.pop(game.player2.user_id, None)


practice_game_manager = PracticeGameManager()
