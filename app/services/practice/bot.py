import asyncio
import random
import time
from typing import Any

from core.config import settings
from schemas.game import GameEvent
from services.game.ability import ability_manager
from services.game.state import GameState, GameStatus, PlayerState
from services.practice.dialogue import *
from services.practice.manager import practice_game_manager

# Bot difficulty multipliers from settings
BOT_PLAYER_CONFIG = {}
BOT_THINKING_MULTIPLIER = settings.BOT_THINKING_MULTIPLIER.split(", ")
BOT_ABILITY_USE_CHANCE = settings.BOT_ABILITY_USE_CHANCE.split(", ")
BOT_ACTION_INTERVAL_MULTIPLIER = settings.BOT_ACTION_INTERVAL_MULTIPLIER.split(", ")
BOT_DAMAGE_MULTIPLIER = settings.BOT_DAMAGE_MULTIPLIER.split(", ")

for i, diff in enumerate(["easy", "medium", "hard"]):
    BOT_PLAYER_CONFIG[diff] = {
        "thinking_multiplier": float(BOT_THINKING_MULTIPLIER[i]),
        "ability_use_chance": float(BOT_ABILITY_USE_CHANCE[i]),
        "action_interval_multiplier": float(BOT_ACTION_INTERVAL_MULTIPLIER[i]),
        "damage_multiplier": float(BOT_DAMAGE_MULTIPLIER[i]),
    }

# Use settings for practice mode constants
DAMAGE_PER_PROBLEM = settings.PRACTICE_DAMAGE_PER_PROBLEM
MAJOR_DAMAGE_MIN = settings.PRACTICE_MAJOR_DAMAGE_MIN
MAJOR_DAMAGE_MAX = settings.PRACTICE_MAJOR_DAMAGE_MAX
MINOR_DAMAGE_MIN = settings.PRACTICE_MINOR_DAMAGE_MIN
MINOR_DAMAGE_MAX = settings.PRACTICE_MINOR_DAMAGE_MAX
HEALING_THRESHOLD = settings.PRACTICE_HEALING_THRESHOLD
HEAL_CHECK_INTERVAL = settings.PRACTICE_HEAL_CHECK_INTERVAL

# Bot timing constants
BASE_ACTION_INTERVAL = settings.PRACTICE_ACTION_INTERVAL
MAX_ADDITIONAL_INTERVAL = settings.PRACTICE_ADDITIONAL_INTERVAL
READING_SPEED = settings.PRACTICE_READING_SPEED
BASE_THINKING_TIME = settings.PRACTICE_THINKING_TIME

BOT_NAME = "Quack"


class BotManager:
    """
    Manager class for practice bot operations.
    """

    def __init__(self):
        self.active_bots: Dict[str, Any] = {}

    def create_bot(
        self, user_id: int, player_state: PlayerState, game_state: GameState
    ) -> Any:
        """
        Create a new bot player.

        :param user_id: Bot user ID
        :param player_state: Bot player state
        :param game_state: The game state the bot belongs to
        :return: A new BotPlayer instance
        """
        bot = BotPlayer(user_id, BOT_NAME, player_state, game_state)
        self.active_bots[str(game_state.id)] = bot
        practice_game_manager.register_game(game_state)
        return bot

    def get_bot_name(self) -> str:
        """
        Get the bot name.

        :return: The bot name
        """
        return BOT_NAME

    async def change_bot_difficulty(self, game_id: str, difficulty: str) -> bool:
        """
        Change the difficulty of a bot.

        :param game_id: The ID of the game
        :param difficulty: The difficulty level to set ("easy", "medium", or "hard")
        :return: True if successful, False otherwise
        """
        bot = self.active_bots.get(str(game_id))
        if bot and difficulty in BOT_PLAYER_CONFIG:
            await bot.change_difficulty(difficulty)
            return True
        return False

    async def start_bot_simulation(self, game_id: str, player_name: str):
        """
        Start the simulation for a bot.

        :param game_id: The ID of the game
        """
        bot = self.active_bots.get(str(game_id))
        if bot:
            await bot.natural_chat(get_welcome_dialogue(player_name))
            await bot.start_simulation()

    async def get_chat_response(self, game_id: str):
        """
        Get a chat response from the bot.

        :return: A chat response string
        """
        bot = self.active_bots.get(str(game_id))
        if bot:
            return await bot.get_chat_response()

    def cleanup_bot(self, game_id: str):
        """
        Clean up a bot instance.

        :param game_id: The ID of the game
        """
        bot = self.active_bots.pop(str(game_id), None)
        if bot:
            bot.cleanup()
        asyncio.create_task(practice_game_manager.cleanup_game(str(game_id)))


practice_bot_manager = BotManager()


class BotPlayer:
    """
    A bot player for practice mode.
    """

    def __init__(
        self, user_id: int, name: str, player_state: PlayerState, game_state: GameState
    ):
        self.user_id = user_id
        self.player_state = player_state
        self.game_state = game_state
        self.is_reading = False
        self.is_thinking = False
        self.next_action_time = 0
        self.name = name
        self.initial_hp = player_state.hp  # Store initial HP to track damage
        self.problem_progress = {}  # Track progress on each problem
        self.heal_task = None  # Task to check healing periodically
        self.last_hp = player_state.hp  # Track HP changes
        self.config = BOT_PLAYER_CONFIG["easy"]  # Default

    async def start_simulation(self):
        """Start the bot simulation in a background task"""
        self.heal_task = asyncio.create_task(self._check_healing_periodically())
        asyncio.create_task(self._simulate_behavior())

    async def change_difficulty(self, difficulty: str):
        """Change the bot's difficulty settings"""
        if difficulty in BOT_PLAYER_CONFIG:
            self.config = BOT_PLAYER_CONFIG[difficulty]
            await self.game_state.broadcast_event(
                GameEvent(
                    type="chat",
                    data={
                        "sender": self.player_state.username,
                        "message": DIFFICULTY_CHANGE_DIALOGUES[difficulty],
                        "timestamp": time.time(),
                    },
                )
            )
        else:
            raise ValueError("Invalid difficulty level")

    async def get_chat_response(self):
        """Get a chat response from the bot"""
        await self.natural_chat(get_chat_response())

    async def _simulate_behavior(self):
        """Simulate bot behavior throughout the game"""
        await self._buy_initial_abilities()

        while self.game_state.status == GameStatus.IN_PROGRESS:
            current_time = time.time()

            if current_time >= self.next_action_time:
                if self.is_reading or self.is_thinking:
                    await asyncio.sleep(1)
                    continue

                # Simulate reading and thinking for every new problem
                problem_index = self.player_state.current_problem_index
                if problem_index < len(self.game_state.problems):
                    problem = self.game_state.problems[problem_index]

                    if problem_index not in self.problem_progress:
                        self.problem_progress[problem_index] = 0

                    if self.problem_progress[problem_index] == 0:
                        await self._simulate_reading(problem)
                        await self._simulate_thinking(problem)

                    await self._execute_action()
                    self._set_next_action_time()

            await asyncio.sleep(1)

    async def _check_healing_periodically(self):
        """Check if healing is needed on a regular interval"""
        while self.game_state.status == GameStatus.IN_PROGRESS:
            try:
                # Check if HP is below threshold and healio is available
                hp_lost = self.initial_hp - self.player_state.hp
                if (
                    self.player_state.hp < HEALING_THRESHOLD
                    and hp_lost > 0
                    and "healio" in self.player_state.abilities
                ):
                    healio = ability_manager.abilities.get("healio")
                    await asyncio.sleep(random.uniform(1, 2))
                    if healio and self.player_state.mana_points >= healio.mp_cost:
                        result = await self._use_ability("healio", True)
                        if result:
                            await self.natural_chat(get_healing_dialogue())
            except Exception as e:
                print(f"Error in heal check: {e}")

            await asyncio.sleep(HEAL_CHECK_INTERVAL)

    async def _buy_initial_abilities(self):
        """Buy initial abilities when game starts"""
        await asyncio.sleep(2)

        abilities_to_buy = ["healio"]
        other_abilities = [
            ability
            for ability in ability_manager.abilities.keys()
            if ability != "healio"
        ]
        random.shuffle(other_abilities)
        abilities_to_buy.extend(other_abilities)

        for ability in abilities_to_buy:
            ability_cost = ability_manager.abilities.get(ability).sp_cost
            if self.player_state.skill_points >= ability_cost:
                await ability_manager.handle_buy_ability(
                    self.game_state, practice_game_manager, self.user_id, ability
                )
                await asyncio.sleep(0.5)

    async def _simulate_reading(self, problem: Any):
        """Simulate reading time based on problem description length"""
        self.is_reading = True

        await self.natural_chat(
            random.choice(READING_PROBLEM_DIALOGUES[problem.difficulty])
        )

        reading_time = len(problem.description) / READING_SPEED * 60
        reading_time = max(5, min(30, reading_time * random.uniform(0.8, 1.2)))

        await asyncio.sleep(reading_time)
        self.is_reading = False

    async def _simulate_thinking(self, problem: Any):
        """Simulate thinking time based on problem difficulty"""
        self.is_thinking = True
        thinking_time = (
            BASE_THINKING_TIME
            * 1
            / BOT_PLAYER_CONFIG[problem.difficulty]["thinking_multiplier"]
        )
        thinking_time = thinking_time * random.uniform(0.8, 1.2)

        await asyncio.sleep(thinking_time)
        self.is_thinking = False

    async def _execute_action(self):
        """Choose and execute an action: deal damage or use ability"""
        problem_index = self.player_state.current_problem_index

        # Either deal damage or use ability
        ability_use_chance = self.config["ability_use_chance"]
        if random.random() < ability_use_chance and self.player_state.abilities:
            available_abilities = [
                a for a in self.player_state.abilities if a != "healio"
            ]
            if available_abilities:
                ability = random.choice(available_abilities)
                await self._use_ability(ability)

        await self._deal_damage(problem_index)

    async def _use_ability(self, ability_id: str, is_healing: bool = False) -> bool:
        """Use an ability"""
        ability = ability_manager.abilities.get(ability_id)
        if ability and self.player_state.mana_points >= ability.mp_cost:
            result = await ability_manager.handle_use_ability(
                self.game_state, practice_game_manager, self.user_id, ability_id
            )

            if result is None:  # None means success
                if not is_healing:
                    await self.game_state.broadcast_event(
                        GameEvent(
                            type="chat",
                            data={
                                "sender": self.player_state.username,
                                "message": get_ability_use_dialogue(),
                                "timestamp": time.time(),
                            },
                        )
                    )

                await self._broadcast_game_state()
                return True

        return False

    async def _deal_damage(self, problem_index: int):
        """Deal damage to player (simulate partial problem solving)"""
        player = self.game_state.get_opponent_state(self.user_id)

        if player and problem_index < len(self.game_state.problems):
            if problem_index not in self.problem_progress:
                self.problem_progress[problem_index] = 0

            progress = self.problem_progress[problem_index]
            damage = 0

            # Welcome to the if-else hell
            # Alternate between big and small damages
            if progress < 30:
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(30, progress + 15)
            elif progress == 30:
                damage = random.randint(MAJOR_DAMAGE_MIN, MAJOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = 45
            elif progress < 70:
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(70, progress + 15)
            elif progress == 70:
                damage = random.randint(MAJOR_DAMAGE_MIN, MAJOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = 85
            elif progress < 100:
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(100, progress + 15)

            damage = int(damage * self.config["damage_multiplier"])
            player.hp = max(0, player.hp - damage)

            await self.natural_chat(get_damage_dialogue())

            await self._broadcast_game_state()

            if self.problem_progress[problem_index] >= 100:
                await self.natural_chat(get_problem_solved_dialogue())

                if (
                    self.player_state.current_problem_index
                    < len(self.game_state.problems) - 1
                ):
                    self.player_state.current_problem_index += 1

            if player.hp <= 0:
                self.game_state.status = GameStatus.FINISHED
                self.game_state.winner = self.player_state.username

                await self.game_state.broadcast_event(
                    GameEvent(
                        type="match_end",
                        data={
                            "winner": self.player_state.username,
                            "winner_id": self.user_id,
                            "reason": "hp_depleted",
                        },
                    )
                )

    async def _broadcast_game_state(self):
        """Broadcast the updated game state to players"""
        await self.game_state.player1.send_event(
            GameEvent(
                type="game_state",
                data=practice_game_manager.create_game_view(
                    self.game_state, self.game_state.player1.user_id
                ).model_dump(),
            )
        )

        if self.game_state.player2.ws:
            await self.game_state.player2.send_event(
                GameEvent(
                    type="game_state",
                    data=practice_game_manager.create_game_view(
                        self.game_state, self.game_state.player2.user_id
                    ).model_dump(),
                )
            )

    def _set_next_action_time(self):
        """Set the time for the next action with difficulty adjustment"""
        interval = BASE_ACTION_INTERVAL * self.config["action_interval_multiplier"]
        additional_random = random.random() * MAX_ADDITIONAL_INTERVAL

        self.next_action_time = time.time() + interval + additional_random

    def cleanup(self):
        """Clean up any running tasks when the bot is destroyed"""
        if self.heal_task:
            self.heal_task.cancel()

    async def natural_chat(self, message: str):
        """
        Split a message into natural sentences and send them as separate chat events to simulate natural typing behavior.

        :param message: The message to send
        """
        sentences = []
        current = ""

        # Split by sentences
        for char in message:
            current += char
            if char in [".", "!", "?"]:
                sentences.append(current)
                current = ""

        if current.strip():
            sentences.append(current)

        # Send each sentence separately
        for sentence in sentences:
            if sentence.endswith("."):
                sentence = sentence[:-1]
            sentence = sentence.strip()
            if not sentence:
                continue

            await asyncio.sleep(random.uniform(2, 3))
            await self.game_state.broadcast_event(
                GameEvent(
                    type="chat",
                    data={
                        "sender": self.player_state.username,
                        "message": sentence,
                        "timestamp": time.time(),
                    },
                )
            )

    async def trigger_bot_healing(self):
        """
        Trigger immediate healing when bot HP drops below threshold.
        The handle_use_ability function already broadcasts the game state update
        """
        await asyncio.sleep(0.8)
        result = await ability_manager.handle_use_ability(
            self.game_state, practice_game_manager, self.user_id, "healio"
        )

        if result is None:
            await self.natural_chat(get_healing_dialogue())
