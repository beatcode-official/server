import asyncio
import time
import traceback
from typing import List, Tuple

from api.endpoints.users.websockets import get_current_user_ws
from core.config import settings
from core.errors.game import *
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from schemas.game import GameEvent
from services.execution.service import code_execution
from services.game.ability import ability_manager
from services.game.manager import game_manager
from services.game.state import GameStatus
from services.problem.service import ProblemManager
from sqlalchemy.orm import Session

router = APIRouter(prefix="/game", tags=["game"])
matchmaker = game_manager.matchmaker


@router.websocket("/queue")
async def queue_websocket(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for the unranked matchmaking queue

    :param websocket: WebSocket object
    :param current_user: User object
    :param db: Database session
    """
    try:
        # Check if the user is already in a game
        if game_manager.get_player_game(current_user.id):
            raise AlreadyInGameError()

        # Only add the user to the queue if they're not already in it
        if not await matchmaker.add_to_queue(websocket, current_user, ranked=False):
            raise AlreadyInQueueError()

        await _process_matchmaking_queue(websocket, current_user, db, ranked=False)

    except WebSocketDisconnect:
        await matchmaker.remove_from_queue(current_user.id)
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in queue websocket: {e}")
        await matchmaker.remove_from_queue(current_user.id)


@router.websocket("/ranked-queue")
async def ranked_queue_websocket(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws),
    db: Session = Depends(get_db),
):
    """Handle ranked matchmaking queue connections."""
    try:
        # Check existing game and queue status
        if game_manager.get_player_game(current_user.id):
            raise AlreadyInGameError()

        if not await matchmaker.add_to_queue(websocket, current_user, ranked=True):
            raise AlreadyInQueueError()

        await _process_matchmaking_queue(websocket, current_user, db, ranked=True)

    except WebSocketDisconnect:
        await matchmaker.remove_from_queue(current_user.id)
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in ranked queue websocket: {e}")
        await matchmaker.remove_from_queue(current_user.id)


async def _process_matchmaking_queue(websocket, current_user, db, ranked=False):
    """
    Process matchmaking queue for user

    :param websocket: WebSocket connection
    :param current_user: Current user
    :param db: Database session
    :param ranked: Boolean indicating ranked or unranked match
    """
    while True:
        try:
            # Manual disconnection doesn't fire the event, so we keep checking for it
            await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            continue
        except asyncio.TimeoutError:
            if ranked:
                match = await matchmaker.get_ranked_match()
                if match:
                    await _setup_ranked_match(match, db)
                    break
            else:
                match = await matchmaker.get_random_player(2)
                if len(match) > 0:
                    await _setup_unranked_match(match, db)
                    break

            await asyncio.sleep(1)


async def _setup_unranked_match(match: List[Tuple[WebSocket, User]], db: Session):
    player1 = match[0][1]
    player2 = match[1][1]

    # Fetch problems
    distribution = matchmaker.get_problem_distribution()
    problems = await ProblemManager.get_problems_by_distribution(db, distribution)

    # Create game and notify players
    game = await game_manager.create_game(player1, player2, problems, "unranked", db)
    await _notify_match_found(match, game.id)


async def _setup_ranked_match(match: List[Tuple[WebSocket, User]], db: Session):
    player1 = match[0][1]
    player2 = match[1][1]

    # Fetch problems based on players' ratings
    distribution = matchmaker.get_problem_distribution(
        ranked=True, rating1=player1.rating, rating2=player2.rating
    )
    problems = await ProblemManager.get_problems_by_distribution(db, distribution)

    # Create game and notify players
    game = await game_manager.create_game(player1, player2, problems, "ranked", db)
    await _notify_match_found(match, game.id)


async def _notify_match_found(match: List[Tuple[WebSocket, User]], match_id: str):
    ws1, player1 = match[0]
    ws2, player2 = match[1]

    match_data = {
        "match_id": match_id,
        "opponent": {
            "username": player2.username,
            "display_name": player2.display_name,
        },
    }

    await ws1.send_json({"type": "match_found", "data": match_data})

    match_data["opponent"] = {
        "username": player1.username,
        "display_name": player1.display_name,
    }

    await ws2.send_json({"type": "match_found", "data": match_data})


@router.websocket("/play/{game_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: str,
    current_user: User = Depends(get_current_user_ws),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for the game

    :param websocket: WebSocket object
    :param game_id: ID of the game
    :param current_user: User object
    :param db: Database session
    """
    game_state = game_manager.active_games.get(game_id)

    # Check if the game exists and is not finished
    if not game_state or game_state.status == GameStatus.FINISHED:
        raise GameNotFoundError()

    # Check if the user is a player in the game
    if current_user.id not in [game_state.player1.user_id, game_state.player2.user_id]:
        raise NotInThisGameError()

    # Get the player state
    player = game_state.get_player_state(current_user.id)
    if not player:
        raise PlayerNotFoundError()

    old_ws = player.ws
    player.ws = websocket

    # Close the old WebSocket connection if it exists
    if old_ws:
        try:
            await old_ws.close(
                code=4000,
                reason="Reconnected from another session. Please close this tab.",
            )
        except Exception:
            pass

    try:
        game_view = game_manager.create_game_view(game_state, current_user.id)
        await websocket.send_json(
            {"type": "game_state", "data": game_view.model_dump()}
        )

        if (
            game_state.status == GameStatus.IN_PROGRESS
            and player.current_problem_index < len(game_state.problems)
        ):
            current_problem = ProblemManager.prepare_problem_for_client(
                game_state.problems[player.current_problem_index]
            )
            await websocket.send_json({"type": "problem", "data": current_problem})

        opponent = game_state.get_opponent_state(current_user.id)
        if opponent and opponent.ws and game_state.status == GameStatus.WAITING:
            game_state.status = GameStatus.IN_PROGRESS

            problem = ProblemManager.prepare_problem_for_client(game_state.problems[0])

            await game_state.broadcast_event(GameEvent(type="game_start", data={}))

            await game_state.broadcast_event(GameEvent(type="problem", data=problem))

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                if game_state.status == GameStatus.FINISHED:
                    break

                # Handle chat messages
                if data["type"] == "chat":
                    await game_state.broadcast_event(
                        GameEvent(
                            type="chat",
                            data={
                                "sender": current_user.username,
                                "message": data["data"]["message"],
                                "timestamp": time.time(),
                            },
                        )
                    )

                elif data["type"] == "ability":
                    error = await ability_manager.handle_ability_message(
                        game_state, game_manager, current_user.id, data["data"]
                    )
                    if error:
                        await websocket.send_json(
                            {"type": "error", "data": {"message": error}}
                        )

                elif data["type"] == "query":
                    game_view = game_manager.create_game_view(
                        game_state, current_user.id
                    )
                    await websocket.send_json(
                        {"type": "game_state", "data": game_view.model_dump()}
                    )
                elif data["type"] == "forfeit":
                    await game_manager.forfeit_game(game_id, current_user.id)
                    await game_manager.handle_game_end(game_state, db)
                elif data["type"] == "submit":
                    current_time = time.time()
                    submission_cooldown = (
                        settings.SUBMISSION_COOLDOWN if not settings.TESTING else 2
                    )
                    if (
                        player.last_submission is not None
                        and current_time - player.last_submission < submission_cooldown
                    ):
                        time_to_wait = submission_cooldown - (
                            current_time - player.last_submission
                        )
                        await player.send_event(
                            GameEvent(
                                type="error",
                                data={
                                    "message": f"You're submitting too fast. Please wait {time_to_wait:.2f}s before submitting again"
                                },
                            )
                        )
                        continue

                    player.last_submission = current_time

                    code = data["data"]["code"]
                    lang = data["data"]["lang"]  # java, cpp, python
                    problem_index = player.current_problem_index
                    problem = game_state.problems[problem_index]

                    validation_data = ProblemManager.get_problem_for_validation(problem)
                    result = await code_execution.execute_code(
                        code,
                        validation_data["method_name"],
                        validation_data["hidden_test_cases"],
                        validation_data["hidden_test_results"],
                        validation_data["sample_test_cases"],
                        validation_data["sample_test_results"],
                        problem.difficulty,
                        getattr(validation_data["compare_func"], lang),
                        lang,
                    )
                    result = result.to_dict()

                    if result["success"]:
                        submission_result = await game_manager.process_submission(
                            game_id,
                            current_user.id,
                            result["summary"]["passed_tests"],
                            result["summary"]["total_tests"],
                        )

                        await player.send_event(
                            GameEvent(
                                type="submission_result",
                                data={**result, **submission_result},
                            )
                        )

                        await game_state.player1.send_event(
                            GameEvent(
                                type="game_state",
                                data=game_manager.create_game_view(
                                    game_state, game_state.player1.user_id
                                ).model_dump(),
                            )
                        )

                        await game_state.player2.send_event(
                            GameEvent(
                                type="game_state",
                                data=game_manager.create_game_view(
                                    game_state, game_state.player2.user_id
                                ).model_dump(),
                            )
                        )

                        if (
                            submission_result["problem_solved"]
                            and problem_index < len(game_state.problems) - 1
                        ):
                            next_problem = ProblemManager.prepare_problem_for_client(
                                game_state.problems[problem_index + 1]
                            )
                            await player.send_event(
                                GameEvent(type="problem", data=next_problem)
                            )

                        if await game_manager.check_game_end(game_id):
                            await game_manager.handle_game_end(game_state, db)
                    else:
                        await player.send_event(
                            GameEvent(type="submission_result", data=result)
                        )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {"message": "An error occurred: " + str(e)},
                        }
                    )
                except Exception:
                    raise e

    except WebSocketDisconnect:
        pass
    except RuntimeError:
        pass
    except Exception as _:
        print(f"Error in game websocket: {traceback.format_exc()}")
