import asyncio
import random
import time
from typing import Dict, Any, Optional, List

from schemas.game import GameEvent
from services.game.ability import ability_manager
from services.problem.service import ProblemManager
from services.game.state import GameState, GameStatus, PlayerState
from services.practice.manager import practice_game_manager
from services.practice.dialogue import *
from core.config import settings

# Bot configuration
BOT_NAMES = ["PracticeBot", "CodeSensei", "AlgoBuddy", "ByteMaster", "QuantumCoder"]

# Bot difficulty multipliers
BOT_DIFFICULTY_CONFIG = {
    "easy": {
        "thinking_multiplier": 1.0,
        "action_interval_multiplier": 1.2,  # Slower actions
        "damage_multiplier": 0.8,  # Lower damage
        "ability_use_chance": 0.5  # Lower chance to use abilities
    },
    "medium": {
        "thinking_multiplier": 2.0, 
        "action_interval_multiplier": 1.0,  # Normal actions
        "damage_multiplier": 1.0,  # Normal damage
        "ability_use_chance": 0.7  # Normal chance to use abilities
    },
    "hard": {
        "thinking_multiplier": 3.0,
        "action_interval_multiplier": 0.7,  # Faster actions
        "damage_multiplier": 1.2,  # Higher damage
        "ability_use_chance": 0.9  # Higher chance to use abilities
    }
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
        self.name = random.choice(BOT_NAMES)
        self.initial_hp = player_state.hp  # Store initial HP to track damage
        self.problem_progress = {}  # Track progress on each problem
        self.heal_task = None  # Task to check healing periodically
        self.last_hp = player_state.hp  # Track HP changes
        
        # Get difficulty from the first problem to adjust bot behavior
        # Default to medium if not available
        if game_state.problems:
            self.difficulty = game_state.problems[0].difficulty.lower()
        else:
            self.difficulty = "medium"
        
        # Get difficulty config
        self.config = BOT_DIFFICULTY_CONFIG.get(self.difficulty, BOT_DIFFICULTY_CONFIG["medium"])
        
    async def start_simulation(self):
        """Start the bot simulation in a background task"""
        self.heal_task = asyncio.create_task(self._check_healing_periodically())
        asyncio.create_task(self._simulate_behavior())
    
    async def _simulate_behavior(self):
        """Simulate bot behavior throughout the game"""
        # Initial setup - buy abilities when game starts
        await self._buy_initial_abilities()
        
        while self.game_state.status == GameStatus.IN_PROGRESS:
            current_time = time.time()
            
            # If it's time for the next action
            if current_time >= self.next_action_time:
                # If bot is still reading/thinking, skip
                if self.is_reading or self.is_thinking:
                    await asyncio.sleep(1)
                    continue
                
                # Get the current problem
                problem_index = self.player_state.current_problem_index
                if problem_index < len(self.game_state.problems):
                    problem = self.game_state.problems[problem_index]
                    
                    # Update difficulty setting based on current problem
                    self.difficulty = problem.difficulty.lower()
                    self.config = BOT_DIFFICULTY_CONFIG.get(self.difficulty, BOT_DIFFICULTY_CONFIG["medium"])
                    
                    # Initialize problem progress if not already done
                    if problem_index not in self.problem_progress:
                        self.problem_progress[problem_index] = 0
                    
                    # Simulate reading the problem if we haven't started it yet
                    if self.problem_progress[problem_index] == 0:
                        await self._simulate_reading(problem)
                    
                    # Simulate thinking about the solution
                    await self._simulate_thinking(problem)
                    
                    # Decide what action to take
                    action = await self._choose_action()
                    
                    # Set the next action time
                    self._set_next_action_time()
            
            await asyncio.sleep(1)
    
    async def _check_healing_periodically(self):
        """Check if healing is needed on a regular interval"""
        while self.game_state.status == GameStatus.IN_PROGRESS:
            try:
                # Check if HP is below threshold and healio is available
                hp_lost = self.initial_hp - self.player_state.hp
                if (self.player_state.hp < HEALING_THRESHOLD and hp_lost > 0 and 
                    "healio" in self.player_state.abilities):
                    
                    healio = ability_manager.abilities.get("healio")
                    if healio and self.player_state.mana_points >= healio.mp_cost:
                        result = await self._use_ability("healio", True)
                        if result:
                            await self.game_state.broadcast_event(
                                GameEvent(
                                    type="chat",
                                    data={
                                        "sender": self.player_state.username,
                                        "message": get_healing_dialogue(),
                                        "timestamp": time.time(),
                                    },
                                )
                            )
            except Exception as e:
                print(f"Error in heal check: {e}")
            
            await asyncio.sleep(HEAL_CHECK_INTERVAL)
    
    async def _buy_initial_abilities(self):
        """Buy initial abilities when game starts"""
        # Wait a bit before buying abilities
        await asyncio.sleep(5)
        
        # Prioritize buying Healio and then other random abilities
        abilities_to_buy = ["healio"]
        # Get other abilities from ability_manager instead of hardcoding
        other_abilities = [ability for ability in ability_manager.abilities.keys() if ability != "healio"]
        random.shuffle(other_abilities)
        abilities_to_buy.extend(other_abilities)
        
        for ability in abilities_to_buy:
            ability_cost = ability_manager.abilities.get(ability).sp_cost
            if self.player_state.skill_points >= ability_cost:
                # Use handle_buy_ability method with our practice game manager
                await ability_manager.handle_buy_ability(
                    self.game_state, 
                    practice_game_manager,
                    self.user_id, 
                    ability
                )
                await asyncio.sleep(1)  # Small delay between purchases
    
    async def _simulate_reading(self, problem: Any):
        """Simulate reading time based on problem description length"""
        self.is_reading = True
        
        # Calculate reading time based on problem description length
        reading_time = len(problem.description) / READING_SPEED * 60
        # Add some randomness
        reading_time = max(5, min(30, reading_time * random.uniform(0.8, 1.2)))
        
        # Simulate reading
        await asyncio.sleep(reading_time)
        self.is_reading = False
    
    async def _simulate_thinking(self, problem: Any):
        """Simulate thinking time based on problem difficulty"""
        self.is_thinking = True
        
        # Base thinking time based on difficulty
        thinking_time = BASE_THINKING_TIME * self.config["thinking_multiplier"]
        # Add some randomness
        thinking_time = thinking_time * random.uniform(0.8, 1.2)
        
        # Simulate thinking
        await asyncio.sleep(thinking_time)
        self.is_thinking = False
    
    async def _choose_action(self):
        """Choose and execute an action: deal damage or use ability"""
        problem_index = self.player_state.current_problem_index
        
        # Randomly decide between dealing damage or using ability based on difficulty
        ability_use_chance = self.config["ability_use_chance"]
        if random.random() < ability_use_chance and self.player_state.abilities:
            # Choose a random ability to use, excluding healio (which has special handling)
            available_abilities = [a for a in self.player_state.abilities if a != "healio"]
            if available_abilities:
                ability = random.choice(available_abilities)
                result = await self._use_ability(ability)
                if result:
                    return f"use_ability_{ability}"
        
        # Deal damage (simulate solving a portion of the problem)
        await self._deal_damage(problem_index)
        return "deal_damage"
    
    async def _use_ability(self, ability_id: str, is_healing: bool = False) -> bool:
        """Use an ability"""
        ability = ability_manager.abilities.get(ability_id)
        if ability and self.player_state.mana_points >= ability.mp_cost:
            # Use handle_use_ability method with our practice game manager
            result = await ability_manager.handle_use_ability(
                self.game_state,
                practice_game_manager,
                self.user_id,
                ability_id
            )
            
            if result is None:  # None means success
                # Only send message for non-healing abilities or if specified
                if not is_healing:
                    # Let the player know what ability was used with a quirky message
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
                
                # Update game state
                await self._broadcast_game_state()
                return True
                
        return False
    
    async def _deal_damage(self, problem_index: int):
        """Deal damage to player (simulate partial problem solving)"""
        # Get the player (opponent of the bot)
        player = self.game_state.get_opponent_state(self.user_id)
        
        if player and problem_index < len(self.game_state.problems):
            # Initialize progress for this problem if not already done
            if problem_index not in self.problem_progress:
                self.problem_progress[problem_index] = 0
            
            # Decide damage amount based on progress
            progress = self.problem_progress[problem_index]
            damage = 0
            
            # Major breakthroughs at ~30% and ~70% progress
            if progress < 30:
                # Minor progress at the beginning
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(30, progress + 15)
            elif progress == 30:
                # First major breakthrough
                damage = random.randint(MAJOR_DAMAGE_MIN, MAJOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = 45
            elif progress < 70:
                # Minor progress in the middle
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(70, progress + 15)
            elif progress == 70:
                # Second major breakthrough
                damage = random.randint(MAJOR_DAMAGE_MIN, MAJOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = 85
            elif progress < 100:
                # Final minor progress
                damage = random.randint(MINOR_DAMAGE_MIN, MINOR_DAMAGE_MAX)
                self.problem_progress[problem_index] = min(100, progress + 15)
            
            # Apply difficulty multiplier
            damage = int(damage * self.config["damage_multiplier"])
            
            # Reduce player's HP
            player.hp = max(0, player.hp - damage)
            
            # Broadcast damage message with quirky dialogue
            await self.game_state.broadcast_event(
                GameEvent(
                    type="chat",
                    data={
                        "sender": self.player_state.username,
                        "message": get_damage_dialogue(),
                        "timestamp": time.time(),
                    },
                )
            )
            
            # Broadcast updated game state
            await self._broadcast_game_state()
            
            # Check if problem is solved (progress reached 100%)
            if self.problem_progress[problem_index] >= 100:
                # Announce problem completion
                await self.game_state.broadcast_event(
                    GameEvent(
                        type="chat",
                        data={
                            "sender": self.player_state.username,
                            "message": get_problem_solved_dialogue(),
                            "timestamp": time.time(),
                        },
                    )
                )
                
                # Move to next problem if available
                if self.player_state.current_problem_index < len(self.game_state.problems) - 1:
                    self.player_state.current_problem_index += 1
            
            # Check if game has ended
            if player.hp <= 0:
                self.game_state.status = GameStatus.FINISHED
                self.game_state.winner = self.player_state.username
                
                # Broadcast game end event
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
        # Send updated game state to player 1
        await self.game_state.player1.send_event(
            GameEvent(
                type="game_state",
                data=practice_game_manager.create_game_view(
                    self.game_state, self.game_state.player1.user_id
                ).model_dump(),
            )
        )
        
        # If player 2 has a websocket, send to them too
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
        # Adjust action interval based on difficulty
        interval = BASE_ACTION_INTERVAL * self.config["action_interval_multiplier"]
        additional_random = random.random() * MAX_ADDITIONAL_INTERVAL
        
        self.next_action_time = time.time() + interval + additional_random
        
    def cleanup(self):
        """Clean up any running tasks when the bot is destroyed"""
        if self.heal_task:
            self.heal_task.cancel()

    async def trigger_bot_healing(self):
        """
        Trigger immediate healing when bot HP drops below threshold.
        The handle_use_ability function already broadcasts the game state update
        """
        # Small delay to make it feel natural rather than instant
        await asyncio.sleep(0.8)
        
        # Use healio ability
        result = await ability_manager.handle_use_ability(
            self.game_state,
            practice_game_manager,
            self.user_id,
            "healio"
        )
        
        # Send healing message if successful
        if result is None:  # None means success
            await self.game_state.broadcast_event(
                GameEvent(
                    type="chat",
                    data={
                        "sender": self.player_state.username,
                        "message": get_healing_dialogue(),
                        "timestamp": time.time(),
                    },
                )
            )


class PracticeBotManager:
    """
    Manager class for practice bot operations.
    """

    def __init__(self):
        self.active_bots: Dict[str, BotPlayer] = {}

    def get_bot_name(self) -> str:
        """
        Generate a random bot name.

        :return: A randomly selected bot name
        """
        return random.choice(BOT_NAMES)

    def create_bot(
        self, user_id: int, player_state: PlayerState, game_state: GameState
    ) -> BotPlayer:
        """
        Create a new bot player.

        :param user_id: Bot user ID
        :param player_state: Bot player state
        :param game_state: The game state the bot belongs to
        :return: A new BotPlayer instance
        """
        bot = BotPlayer(user_id, player_state, game_state)
        self.active_bots[str(game_state.id)] = bot

        # Register the game with our practice game manager
        practice_game_manager.register_game(game_state)

        return bot

    async def start_bot_simulation(self, game_id: str):
        """
        Start the simulation for a bot.

        :param game_id: The ID of the game
        """
        bot = self.active_bots.get(str(game_id))
        if bot:
            await bot.start_simulation()

    def cleanup_bot(self, game_id: str):
        """
        Clean up a bot instance.

        :param game_id: The ID of the game
        """
        self.active_bots.pop(str(game_id), None)

        # Clean up the game from our practice game manager
        asyncio.create_task(practice_game_manager.cleanup_game(str(game_id)))


# Create a singleton instance
practice_bot_manager = PracticeBotManager()
