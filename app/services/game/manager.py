import asyncio
import uuid
import time
from typing import Dict, List, Optional

from core.config import settings
from db.models.problem import Problem
from db.models.user import User
from db.models.game import Match
from services.game.matchmaker import Matchmaker
from services.game.state import GameState, GameStatus, PlayerState
from sqlalchemy.orm import Session
from schemas.game import GameEvent, MatchResult


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
        self.hp_multiplier = {
            "easy": settings.HP_MULTIPLIER_EASY,
            "medium": settings.HP_MULTIPLIER_MEDIUM,
            "hard": settings.HP_MULTIPLIER_HARD,
        }

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
            ),
            player2=PlayerState(
                user_id=player2.id,
                username=player2.username,
                display_name=player2.display_name,
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

    def get_player_game(self, player_id: int) -> Optional[GameState]:
        """
        Gets the game that a player is currently in.

        :param player_id: The ID of the player.
        :return: The game that the player is in, if any.
        """
        game_id = self.player_to_game.get(player_id)
        return self.active_games.get(game_id) if game_id else None

    def calculate_hp_deduction(self, test_cases_solved: int, difficulty: str) -> int:
        """
        # SUBJECT TO CHANGE
        Calculates the HP deduction for a player based on the number of test cases solved and the problem difficulty.

        :param test_cases_solved: The number of test cases solved.
        :param difficulty: The difficulty of the problem.
        :return: The HP deduction.
        """
        base_deduction = self.hp_deduction * test_cases_solved

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
                test_cases_solved - prev_solved,  # Deduct HP based on new test cases solved only
                current_problem.difficulty,
            )
            opponent.hp = max(0, opponent.hp - hp_deduction)
            player.partial_progress[player.current_problem_index] = test_cases_solved

            # Check if the player has solved the problem
            if test_cases_solved == total_test_cases:
                player.problems_solved += 1
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
            game.player1.hp <= 0 or
            game.player2.hp <= 0 or
            game.player1.current_problem_index == len(game.problems) or
            game.player2.current_problem_index == len(game.problems)
        ):
            game.winner = await self.get_winner(game)

            game.status = GameStatus.FINISHED
            return True

        return False

    async def handle_game_end(
        self,
        game_state: GameState,
        db: Session
    ):
        """
        Handle the end of a game like saving the match data and cleaning up the game

        :param game_state: GameState object
        :param db: Database session
        """
        # Prevent multiple cleanup calls
        if game_state.is_cleaning_up:
            return

        game_state.is_cleaning_up = True

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
                game_state.player1.user_id if game_state.winner == game_state.player1.username
                else game_state.player2.user_id if game_state.winner == game_state.player2.username
                else None
            ),
            problems=[p.id for p in game_state.problems],
        )

        try:
            db.add(match)
            db.commit()
        except Exception as e:
            print(f"Error saving match: {e}")
            db.rollback()

        # Broadcast the match result to the players
        result = MatchResult(
            winner_username=game_state.winner,
            player1_username=game_state.player1.username,
            player2_username=game_state.player2.username,
            player1_hp=game_state.player1.hp,
            player2_hp=game_state.player2.hp,
            player1_problems_solved=game_state.player1.problems_solved,
            player2_problems_solved=game_state.player2.problems_solved,
            player1_partial_progress=game_state.player1.partial_progress,
            player2_partial_progress=game_state.player2.partial_progress,
            match_type=game_state.match_type,
        )

        await game_state.broadcast_event(GameEvent(
            type="match_end",
            data=result.model_dump()
        ))

        await self.cleanup_game(game_state.id)

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
