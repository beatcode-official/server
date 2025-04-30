import asyncio
import logging
import random
import time
from typing import Any

from schemas.game import GameEvent
from services.game.ability import ability_manager
from services.game.state import GameState, GameStatus, PlayerState
from services.practice.constants import *
from services.practice.dialogue import *
from services.practice.manager import practice_game_manager

logger = logging.getLogger(__name__)


class BotPlayer:
    """
    A bot player for practice mode.
    """

    def __init__(self, user_id: int, player_state: PlayerState, game_state: GameState):
        self.user_id = user_id
        self.player_state = player_state
        self.game_state = game_state
        self.is_reading = False
        self.is_thinking = False
        self.next_action_time = 0
        self.initial_hp = player_state.hp
        self.problem_progress = {}
        self.simulation_task = None
        self.last_hp = player_state.hp
        self.config = BOT_PLAYER_CONFIG["easy"]
        self._chat_queue = asyncio.Queue()
        self._chat_task = asyncio.create_task(self._chat_worker())

    async def start_simulation(self, player_name: str):
        """Start the bot simulation in a background task"""
        if player_name and self._chat_queue.empty():
            self._chat_queue.put_nowait(
                get_welcome_dialogue(player_name)
            )  # greet player first

        if self.simulation_task:
            self.simulation_task.cancel()

        self.simulation_task = asyncio.create_task(self._simulate_behavior())

    async def change_difficulty(self, difficulty: str):
        """Change the bot's difficulty settings"""
        if difficulty in BOT_PLAYER_CONFIG:
            self.config = BOT_PLAYER_CONFIG[difficulty]
            await self.natural_chat(DIFFICULTY_CHANGE_DIALOGUES[difficulty])
        else:
            await self.natural_chat("Invalid difficulty")

    async def respond_to_chat(self):
        """Get a chat response from the bot (maybe add LLM later idk)"""
        await self.natural_chat(get_chat_response())

    async def respond_to_ability_use(self):
        """Respond to player using ability"""
        await self.natural_chat(get_ability_received_dialogue())

    async def _simulate_behavior(self):
        """Run bot simulation throughout the game"""
        try:
            await self._buy_initial_abilities()

            while self.game_state.status == GameStatus.IN_PROGRESS:
                current_time = time.time()

                if current_time >= self.next_action_time:
                    if self.is_reading or self.is_thinking:
                        await asyncio.sleep(1)
                        continue

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
        except asyncio.CancelledError:
            logger.info(f"Bot simulation for game {self.game_state.id} cancelled.")
        except Exception as e:
            logger.exception(
                f"Error in bot simulation for game {self.game_state.id}: {e}"
            )

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
            ability_data = ability_manager.abilities.get(ability)
            if not ability_data:
                continue
            ability_cost = ability_data.sp_cost
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

    async def _use_ability(self, ability_id: str) -> bool:
        """Use an ability"""
        ability = ability_manager.abilities.get(ability_id)
        if ability and self.player_state.mana_points >= ability.mp_cost:
            result = await ability_manager.handle_use_ability(
                self.game_state, practice_game_manager, self.user_id, ability_id
            )

            if result is None:
                if ability_id != "healio":
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
                else:
                    if player.hp > 0:
                        self.game_state.status = GameStatus.FINISHED
                        self.game_state.winner = self.player_state.username
                        await self.game_state.broadcast_event(
                            GameEvent(
                                type="match_end",
                                data={
                                    "winner": self.player_state.username,
                                    "winner_id": self.user_id,
                                    "reason": "problems_solved",
                                },
                            )
                        )

            if player.hp <= 0 and self.game_state.status != GameStatus.FINISHED:
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
        if self.game_state.status == GameStatus.FINISHED:
            return

        if self.game_state.player1.ws:
            await self.game_state.player1.send_event(
                GameEvent(
                    type="game_state",
                    data=practice_game_manager.create_game_view(
                        self.game_state, self.game_state.player1.user_id
                    ).model_dump(),
                )
            )

        if self.game_state.player2 and self.game_state.player2.ws:
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
        if self.simulation_task:
            self.simulation_task.cancel()
        if self._chat_task:
            self._chat_task.cancel()

    async def natural_chat(self, message: str):
        """
        Enqueue a message to be sent as natural chat, ensuring sequential delivery.
        """
        await self._chat_queue.put(message)

    async def _process_natural_chat(self, message: str):
        """
        Split a message into natural sentences and send them as separate chat events
        to simulate natural typing behavior. Handles consecutive punctuation.

        :param message: The message to send
        """
        sentences = []
        start_index = 0
        punctuation = {".", "!", "?"}

        for i, char in enumerate(message):
            if char in punctuation:
                is_last_char = i == len(message) - 1
                is_group_char = (
                    i + 1 < len(message) and message[i + 1] not in punctuation
                )

                if is_last_char or is_group_char:
                    sentence = message[start_index : i + 1].strip()
                    if sentence:
                        sentences.append(sentence)
                    start_index = i + 1

        remaining = message[start_index:].strip()
        if remaining:
            sentences.append(remaining)

        for sentence in sentences:
            if not sentence:
                continue

            typing_delay = len(sentence) * 0.05 + random.uniform(0.5, 1.5)
            await asyncio.sleep(typing_delay)

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
        """
        # Check if game ended or bot doesn't have healio or enough mana
        if self.game_state.status != GameStatus.IN_PROGRESS:
            return
        if "healio" not in self.player_state.abilities:
            return

        healio = ability_manager.abilities.get("healio")
        if not healio or self.player_state.mana_points < healio.mp_cost:
            return

        await asyncio.sleep(random.uniform(0.5, 1.2))  # Reaction time

        # Re-check mana points after delay, in case mana changed
        if self.player_state.mana_points >= healio.mp_cost:
            success = await self._use_ability("healio")
            if success:
                await self.natural_chat(get_healing_dialogue())

    async def _chat_worker(self):
        """
        Background task to process chat messages sequentially.
        """
        while True:
            try:
                message = await self._chat_queue.get()
                await self._process_natural_chat(message)
                self._chat_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    f"Error in chat worker for game {self.game_state.id}: {e}"
                )
                await asyncio.sleep(1)
