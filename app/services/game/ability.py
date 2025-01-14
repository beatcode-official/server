from typing import Dict, Optional
from pydantic import BaseModel
from schemas.game import GameEvent
from services.game.manager import GameManager
from services.game.state import GameState


class Ability(BaseModel):
    """
    A class to represent an ability in the game

    :param id: The unique identifier of the ability
    :param sp_cost: The amount of skill points required to buy the ability
    :param mp_cost: The amount of mana points required to use the ability
    """
    sp_cost: int
    mp_cost: int


class AbilityManager:
    """
    Class to manage all ability-related operations
    """

    def __init__(self):
        self.abilities: Dict[str, Ability] = {
            "healio": Ability(sp_cost=10, mp_cost=20),
            "deletio": Ability(sp_cost=10, mp_cost=5),
            "syntaxio": Ability(sp_cost=10, mp_cost=5),
            "lightio": Ability(sp_cost=10, mp_cost=5),
            "hugio": Ability(sp_cost=10, mp_cost=5),
            "smallio": Ability(sp_cost=10, mp_cost=5),
        }

    async def handle_ability_message(
        self,
        game_state: GameState,
        game_manager: GameManager,
        player_id: int,
        message: Dict
    ) -> Optional[str]:
        """
        Handle an ability message from the client

        :param game_state: The current game state
        :param player_id: The id of the player sending the message
        :param message: The message sent by the player
        :return: Error message if any
        """
        action = message.get("action")
        if action == "buy":
            return await self.handle_buy_ability(
                game_state,
                game_manager,
                player_id,
                message.get("ability_id")
            )
        elif action == "use":
            return await self.handle_use_ability(
                game_state,
                game_manager,
                player_id,
                message.get("ability_id")
            )

        return "Invalid action"

    async def handle_buy_ability(
        self,
        game_state: GameState,
        game_manager: GameManager,
        player_id: int,
        ability_id: str
    ) -> Optional[str]:
        """
        Handle ability purchases

        :param game_state: The current game state
        :param player_id: The id of the player buying the ability
        :param ability_id: The id of the ability to buy
        """
        ability = self.abilities.get(ability_id)
        if not ability:
            return "Invalid ability id"

        player = game_state.get_player_state(player_id)
        if not player:
            return "Player not found"

        if ability_id in player.abilities:
            return "Ability already bought"

        if player.skill_points < ability.sp_cost:
            return "Not enough skill points"

        player.skill_points -= ability.sp_cost
        player.abilities.append(ability_id)

        await game_state.broadcast_event(GameEvent(
            type="ability_bought",
            data={
                "player": player.username,
                "ability": ability_id
            }
        ))

        # Send updated player states to both players
        await game_state.player1.send_event(GameEvent(
            type="game_state",
            data=game_manager.create_game_view(
                game_state,
                game_state.player1.user_id
            ).model_dump()
        ))

        await game_state.player2.send_event(GameEvent(
            type="game_state",
            data=game_manager.create_game_view(
                game_state,
                game_state.player2.user_id
            ).model_dump()
        ))

        return None

    async def handle_use_ability(
        self,
        game_state: GameState,
        game_manager: GameManager,
        player_id: int,
        ability_id: str
    ) -> Optional[str]:
        """
        Handle ability uses

        :param game_state: The current game state
        :param player_id: The id of the player using the ability
        :param ability_id: The id of the ability to use
        """
        ability = self.abilities.get(ability_id)
        if not ability:
            return "Invalid ability id"

        player = game_state.get_player_state(player_id)
        opponent = game_state.get_opponent_state(player_id)
        if not player or not opponent:
            return "Player not found"

        if ability_id not in player.abilities:
            return "Don't own this ability"

        if player.mana_points < ability.mp_cost:
            return "Not enough mana points"

        player.mana_points -= ability.mp_cost

        # Handle abilities here, define new methods if needed
        if ability_id == "healio":
            player.hp += 20  # Heal for 20

        await game_state.broadcast_event(GameEvent(
            type="ability_used",
            data={
                "player": player.username,
                "ability": ability_id
            }
        ))

        # Send updated player states to both players
        await game_state.player1.send_event(GameEvent(
            type="game_state",
            data=game_manager.create_game_view(
                game_state,
                game_state.player1.user_id
            ).model_dump()
        ))

        await game_state.player2.send_event(GameEvent(
            type="game_state",
            data=game_manager.create_game_view(
                game_state,
                game_state.player2.user_id
            ).model_dump()
        ))

        return None


ability_manager = AbilityManager()
