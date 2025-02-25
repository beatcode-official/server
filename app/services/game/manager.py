import asyncio
import random
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from core.config import settings
from db.models.game import Match
from db.models.problem import Problem
from db.models.user import User
from schemas.game import GameEvent, GameView
from services.game.matchmaker import Matchmaker
from services.game.state import GameState, GameStatus, PlayerState
from services.problem.service import ProblemManager
from services.room.service import room_service
from services.room.state import RoomSettings, RoomStatus
from sqlalchemy.orm import Session


class GameManager:
    """
    A service class for managing game state and operations.
    """

    def __init__(self):
        self.active_games: Dict[str, GameState] = {}
        self.player_to_game: Dict[int, str] = {}  # Maps player ID to game ID
        self.matchmaker = Matchmaker()
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.db_sessions: Dict[str, Session] = {}
        self.hp_deduction = settings.HP_DEDUCTION_BASE
        easy, medium, hard = [float(x) for x in settings.HP_MULTIPLIER.split(",")]
        self.hp_multiplier = {
            "easy": easy,
            "medium": medium,
            "hard": hard,
        }

    def create_game_view(self, game_state: GameState, user_id: int) -> GameView:
        """
        Create a GameView object from a GameState object

        :param game_state: GameState object
        :param user_id: ID of the user requesting the view
        """
        is_player1 = game_state.player1.user_id == user_id
        player = game_state.player1 if is_player1 else game_state.player2
        opponent = game_state.player2 if is_player1 else game_state.player1
        rating_change = (
            game_state.player1_rating_change
            if is_player1
            else game_state.player2_rating_change
        )

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
            rating_change=rating_change,
            skill_points=player.skill_points,
            mana_points=player.mana_points,
            abilities=player.abilities,
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

    async def check_timeout(self, game_id: str, db: Session):
        """
        Periodically check if a game has timed out.

        :param game_id: The ID of the game to check.
        :param db: The database session.
        """
        while True:
            try:
                game = self.active_games.get(game_id)
                if not game or game.status == GameStatus.FINISHED:
                    break

                if game.is_timed_out():
                    game.status = GameStatus.FINISHED
                    game.winner = await self.get_winner(game)
                    await self.handle_game_end(game, db)
                    break

                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in timeout checker: {e}")
                break

    async def create_game(
        self,
        player1: User,
        player2: User,
        problems: List[Problem],
        match_type: str,
        db: Session,
    ) -> GameState:
        """
        Creates a new game between two players.

        :param player1: The first player.
        :param player2: The second player.
        :param problems: The list of problems for the match.
        :param match_type: The type of the match.
        :param db: The database session.
        """
        game_id = uuid.uuid4().hex

        # Create the corresponding game state object
        game = GameState(
            id=game_id,
            status=GameStatus.WAITING,
            player1=PlayerState(
                user_id=player1.id,
                username=player1.username,
                display_name=player1.display_name,
                rating=player1.rating,
                avatar_url=player1.avatar_url,
            ),
            player2=PlayerState(
                user_id=player2.id,
                username=player2.username,
                display_name=player2.display_name,
                rating=player2.rating,
                avatar_url=player2.avatar_url,
            ),
            problems=problems,
            start_time=time.time(),
            match_type=match_type,
        )

        # Add the game to the active games and player to game mappings
        self.active_games[game_id] = game
        self.player_to_game[player1.id] = game_id
        self.player_to_game[player2.id] = game_id

        # Start the timeout checker task
        timeout_task = asyncio.create_task(self.check_timeout(game_id, db))
        self.timeout_tasks[game_id] = timeout_task
        game.timeout_task = timeout_task

        return game

    async def create_game_with_settings(
        self,
        player1: User,
        player2: User,
        room_settings: RoomSettings,
        db: Session,
    ) -> GameState:
        """
        Creates a new game with custom room settings

        :param player1: The first player
        :param player2: The second player
        :param room_settings: The room settings
        :param db: The database session
        """
        game_id = uuid.uuid4().hex

        # Get problems based on distribution settings
        if room_settings.distribution_mode == "fixed":
            distribution = {
                "easy": int(room_settings.prob_easy * room_settings.problem_count),
                "medium": int(room_settings.prob_medium * room_settings.problem_count),
                "hard": int(
                    room_settings.problem_count
                    - int(room_settings.prob_easy * room_settings.problem_count)
                    - int(room_settings.prob_medium * room_settings.problem_count)
                ),
            }
        else:
            distribution = defaultdict(int)
            for _ in range(room_settings.problem_count):
                r = random.random()
                if r < room_settings.prob_easy:
                    distribution["easy"] += 1
                elif r < room_settings.prob_easy + room_settings.prob_medium:
                    distribution["medium"] += 1
                else:
                    distribution["hard"] += 1

        problems = await ProblemManager.get_problems_by_distribution(
            db, dict(distribution)
        )

        # Create the corresponding game state object
        game = GameState(
            id=game_id,
            status=GameStatus.WAITING,
            player1=PlayerState(
                user_id=player1.id,
                username=player1.username,
                display_name=player1.display_name,
                avatar_url=player1.avatar_url,
                hp=room_settings.starting_hp,
                skill_points=room_settings.starting_sp,
                mana_points=room_settings.starting_mp,
            ),
            player2=PlayerState(
                user_id=player2.id,
                username=player2.username,
                display_name=player2.display_name,
                avatar_url=player2.avatar_url,
                hp=room_settings.starting_hp,
                skill_points=room_settings.starting_sp,
                mana_points=room_settings.starting_mp,
            ),
            problems=problems,
            start_time=time.time(),
            match_type="custom",
            custom_settings={
                "hp_multiplier": {
                    "easy": room_settings.hp_multiplier_easy,
                    "medium": room_settings.hp_multiplier_medium,
                    "hard": room_settings.hp_multiplier_hard,
                },
                "base_hp_deduction": room_settings.base_hp_deduction,
                "mana_recharge": room_settings.mana_recharge,
            },
        )

        self.active_games[game_id] = game
        self.player_to_game[player1.id] = game_id
        self.player_to_game[player2.id] = game_id

        # Start the timeout checker task
        timeout_task = asyncio.create_task(self.check_timeout(game_id, db))
        self.timeout_tasks[game_id] = timeout_task
        game.timeout_task = timeout_task

        return game

    def get_player_game(self, player_id: int) -> Optional[GameState]:
        """
        Gets the game that a player is currently in.

        :param player_id: The ID of the player.
        :return: The game that the player is in, if any.
        """
        game_id = self.player_to_game.get(player_id)
        return self.active_games.get(game_id) if game_id else None

    def calculate_hp_deduction(
        self, test_cases_solved: int, difficulty: str, game_state: GameState
    ) -> int:
        """
        # SUBJECT TO CHANGE
        Calculates the HP deduction for a player based on the number of test cases solved and the problem difficulty.

        :param test_cases_solved: The number of test cases solved.
        :param difficulty: The difficulty of the problem.
        :param game_state: The game state object.
        :return: The HP deduction.
        """
        # Use custom base deduction if available, otherwise use default
        if (
            game_state.custom_settings
            and "base_hp_deduction" in game_state.custom_settings
        ):
            base_deduction = (
                game_state.custom_settings["base_hp_deduction"] * test_cases_solved
            )
        else:
            base_deduction = self.hp_deduction * test_cases_solved

        # Use custom multipliers if available, otherwise use default
        if game_state.custom_settings and "hp_multiplier" in game_state.custom_settings:
            multiplier = game_state.custom_settings["hp_multiplier"].get(
                difficulty.lower(), 1
            )
        else:
            multiplier = self.hp_multiplier.get(difficulty.lower(), 1)

        return int(base_deduction * multiplier)

    async def process_submission(
        self,
        game_id: str,
        player_id: int,
        test_cases_solved: int,
        total_test_cases: int,
    ) -> Dict:
        """
        Processes a submission from a player.

        :param game_id: The ID of the game.
        :param player_id: The ID of the player.
        :param test_cases_solved: The number of test cases solved.
        :param total_test_cases: The total number of test cases.
        :return: A dictionary containing the HP deduction and whether the problem was solved.
        """
        game = self.active_games[game_id]
        player = game.get_player_state(player_id)
        opponent = game.get_opponent_state(player_id)

        current_problem = game.problems[player.current_problem_index]
        prev_solved = player.partial_progress.get(player.current_problem_index, 0)
        hp_deduction = 0

        # Only update the player's state if they have made progress
        if test_cases_solved > prev_solved:
            hp_deduction = self.calculate_hp_deduction(
                test_cases_solved
                - prev_solved,  # Deduct HP based on new test cases solved only
                current_problem.difficulty,
                game,
            )
            opponent.hp = max(0, opponent.hp - hp_deduction)
            player.partial_progress[player.current_problem_index] = test_cases_solved

            # Check if the player has solved the problem
            if test_cases_solved == total_test_cases:
                player.problems_solved += 1

                mana_recharge = (
                    game.custom_settings.get("mana_recharge", settings.MANA_RECHARGE)
                    if game.custom_settings
                    else settings.MANA_RECHARGE
                )

                player.mana_points += mana_recharge  # Recharge mana
                if player.current_problem_index < len(game.problems) - 1:
                    player.current_problem_index += 1

        return {
            "deducted_hp": hp_deduction if test_cases_solved > prev_solved else 0,
            "problem_solved": test_cases_solved == total_test_cases,
        }

    async def check_game_end(self, game_id: str) -> bool:
        """
        Checks if the game has ended.

        :param game_id: The ID of the game.
        :return: True if the game has ended, False otherwise
        """
        game = self.active_games[game_id]

        # If one player's HP reaches 0 or one player has solved all problems the game ends
        if (
            game.player1.hp <= 0
            or game.player2.hp <= 0
            or game.player1.problems_solved == len(game.problems)
            or game.player2.problems_solved == len(game.problems)
        ):
            game.winner = await self.get_winner(game)

            game.status = GameStatus.FINISHED
            return True

        return False

    async def handle_game_end(self, game_state: GameState, db: Session):
        """
        Handle the end of a game like saving the match data and cleaning up the game

        :param game_state: GameState object
        :param db: Database session
        """
        # Prevent multiple cleanup calls
        if game_state.is_cleaning_up:
            return

        game_state.is_cleaning_up = True

        if game_state.match_type == "ranked":
            await self.handle_ranked_match_end(game_state, db)

        # Save the match data
        match = Match(
            player1_id=game_state.player1.user_id,
            player2_id=game_state.player2.user_id,
            player1_hp=game_state.player1.hp,
            player2_hp=game_state.player2.hp,
            player1_problems_solved=game_state.player1.problems_solved,
            player2_problems_solved=game_state.player2.problems_solved,
            player1_partial_progress=game_state.player1.partial_progress,
            player2_partial_progress=game_state.player2.partial_progress,
            start_time=game_state.start_time,
            end_time=time.time(),
            match_type=game_state.match_type,
            winner_id=(
                game_state.player1.user_id
                if game_state.winner == game_state.player1.username
                else (
                    game_state.player2.user_id
                    if game_state.winner == game_state.player2.username
                    else None
                )
            ),
            problems=[p.id for p in game_state.problems],
            player1_rating_change=game_state.player1_rating_change,
            player2_rating_change=game_state.player2_rating_change,
        )

        try:
            db.add(match)
            db.commit()
        except Exception as e:
            print(f"Error saving match: {e}")
            db.rollback()

        # Find the room this game belongs to
        room = next(
            (
                room
                for room in room_service.rooms.values()
                if room.game_id == game_state.id
            ),
            None,
        )

        # If room exists, reset its status
        if room:
            room.status = RoomStatus.WAITING
            room.game_id = None
            room.reset_ready_status()

            # Get users for room view
            users = {
                room.host_id: db.query(User).filter(User.id == room.host_id).first(),
            }
            if room.guest_id:
                users[room.guest_id] = (
                    db.query(User).filter(User.id == room.guest_id).first()
                )

            # Broadcast updated room state
            await room.broadcast(
                {
                    "type": "room_update",
                    "data": room_service.create_room_view(room, users).model_dump(),
                }
            )

        # Broadcast the match result to the players
        await game_state.player1.send_event(
            GameEvent(
                type="match_end",
                data=self.create_game_view(
                    game_state, game_state.player1.user_id
                ).model_dump(),
            )
        )

        await game_state.player2.send_event(
            GameEvent(
                type="match_end",
                data=self.create_game_view(
                    game_state, game_state.player2.user_id
                ).model_dump(),
            )
        )

        await self.cleanup_game(game_state.id)

    async def handle_ranked_match_end(self, game_state: GameState, db: Session):
        """
        Handle the end of a ranked match including rating calculations

        :param game_state: The game state
        :param db: Database session
        """
        # Skip rating calculation if the game is a draw
        if game_state.winner:
            # Get winner and loser states
            winner = (
                game_state.player1
                if game_state.winner == game_state.player1.username
                else game_state.player2
            )
            loser = (
                game_state.player2
                if game_state.winner == game_state.player1.username
                else game_state.player1
            )

            # Get users from database
            winner_user = db.query(User).filter(User.id == winner.user_id).first()
            loser_user = db.query(User).filter(User.id == loser.user_id).first()

            # Calculate rating change
            winner_change = self.matchmaker.ranked_service.calculate_rating_change(
                winner_user.rating, loser_user.rating, True
            )

            loser_change = self.matchmaker.ranked_service.calculate_rating_change(
                loser_user.rating, winner_user.rating, False
            )

            # Update ratings
            winner_user.rating = max(0, winner_user.rating + winner_change)
            loser_user.rating = max(0, loser_user.rating + loser_change)

            # Save rating changes
            game_state.player1_rating_change = (
                winner_change
                if game_state.winner == game_state.player1.username
                else loser_change if loser_user.rating > 0 else 0
            )
            game_state.player2_rating_change = (
                winner_change
                if game_state.winner == game_state.player2.username
                else loser_change if loser_user.rating > 0 else 0
            )

    async def forfeit_game(self, game_id: str, player_id: int):
        """
        Forfeits the game for a player.

        :param game_id: The ID of the game.
        :param player_id: The ID of the player forfeiting
        """

        game = self.active_games[game_id]
        game.winner = game.get_opponent_state(player_id).username
        game.status = GameStatus.FINISHED

    async def cleanup_game(self, game_id: str):
        """
        Cleans up a game after it has ended.

        :param game_id: The ID of the game.
        """
        # Cancel the timeout checker task if it exists
        timeout_task = self.timeout_tasks.pop(game_id, None)
        if timeout_task:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

        # Remove the game from the active games and player to game mappings
        game = self.active_games.pop(game_id, None)
        if game:
            self.player_to_game.pop(game.player1.user_id, None)
            self.player_to_game.pop(game.player2.user_id, None)


game_manager = GameManager()
