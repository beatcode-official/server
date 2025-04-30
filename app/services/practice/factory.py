from typing import Dict

from services.game.state import GameState, PlayerState
from services.practice.bot import BotPlayer


class BotFactory:
    """Factory class for keeping track of active bots"""

    def __init__(self):
        self.bots: Dict[str, BotPlayer] = {}

    def create_bot(
        self, game_id: str, bot_id: int, bot_state: PlayerState, game_state: GameState
    ) -> bool:
        if game_id in self.bots:
            return False
        self.bots[game_id] = BotPlayer(bot_id, bot_state, game_state)
        return True

    def get_bot(self, game_id: str):
        return self.bots.get(game_id)

    def delete_bot(self, game_id: str):
        if game_id in self.bots:
            self.bots[game_id].cleanup()
            del self.bots[game_id]
            return True
        return False


bot_factory = BotFactory()
