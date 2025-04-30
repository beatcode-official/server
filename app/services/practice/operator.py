import asyncio
import random
from typing import Dict, Optional

from services.game.ability import ability_manager
from services.game.state import GameState, PlayerState
from services.practice.bot import BotPlayer
from services.practice.constants import BOT_PLAYER_CONFIG, HEALING_THRESHOLD
from services.practice.manager import practice_game_manager


class PracticeGameOperator:
    def __init__(self):
        self.manager = practice_game_manager
        self.active_bots: Dict[str, BotPlayer] = {}

    def register_game(self, game_state: GameState):
        self.manager.active_games[game_state.id] = game_state

    def get_game_view(self, game_state: GameState, user_id: int) -> dict:
        return self.manager.create_game_view(game_state, user_id).model_dump()

    async def process_submission(
        self,
        game_id: str,
        player_id: int,
        test_cases_solved: int,
        total_test_cases: int,
    ) -> Dict:
        return await self.manager.process_submission(
            game_id, player_id, test_cases_solved, total_test_cases
        )

    async def create_bot(
        self, bot_id: int, bot_state: PlayerState, game_state: GameState
    ):
        bot = BotPlayer(bot_id, bot_state, game_state)
        self.active_bots[game_state.id] = bot

    async def run_bot(self, game_id: str, player_name: str):
        """
        Start the simulation for the bot in a specific game.

        :param game_id: The ID of the game
        :param player_name: The human player's name for dialogue
        """
        if game_id in self.active_bots:
            bot = self.active_bots[game_id]
            await bot.start_simulation(player_name)

    # include message when equipped with llm later
    async def handle_chat_message(self, game_id: str):
        """
        Trigger the bot in a specific game to generate a chat response.

        :param game_id: The ID of the game
        :param message: The chat message
        """
        if game_id in self.active_bots:
            bot = self.active_bots[game_id]
            await bot.respond_to_chat()

    async def handle_ability_message(
        self,
        game_state: GameState,
        player_id: int,
        message: Dict,
    ) -> Optional[str]:
        """
        Handle ability messages in practice mode, such as how bot should respond when receiving ability effects

        :param game_state: The current game state
        :param player_id: The id of the player sending the message
        :param message: The ability message
        :return: Error message if any
        """
        error = await ability_manager.handle_ability_message(
            game_state, self.manager, player_id, message["data"]
        )
        if error:
            return error

        action = message["data"].get("action", "")
        ability_id_used = message["data"].get("ability_id", "")
        bot = self.active_bots[game_state.id]

        if not bot:
            return None
        if action == "use" and ability_id_used != "healio":
            await bot.respond_to_ability_use()

    async def heal_bot_if_needed(self, game_id: str, bot_state: PlayerState):
        bot = self.active_bots.get(game_id)

        if bot and bot_state.hp < HEALING_THRESHOLD and "healio" in bot_state.abilities:
            await asyncio.sleep(random.randint(1, 5))
            healio = ability_manager.abilities.get("healio")
            if healio and bot_state.mana_points >= healio.mp_cost:
                asyncio.create_task(bot.trigger_bot_healing())

    async def change_bot_difficulty(self, game_id: str, difficulty: str) -> bool:
        """
        Change the difficulty of the bot for a specific game.

        :param game_id: The ID of the game
        :param difficulty: The difficulty level ("easy", "medium", "hard")
        :return: True if successful, False otherwise
        """
        bot = self.active_bots[game_id]
        if bot and difficulty in BOT_PLAYER_CONFIG:
            await bot.change_difficulty(difficulty)
            return True
        return False

    async def cleanup_game(self, game_id: str) -> None:
        """
        Cleans up a game after it has ended.

        :param game_id: The ID of the game.
        """
        if game_id in self.active_bots:
            bot = self.active_bots[game_id]
            bot.cleanup()
            del self.active_bots[game_id]
