import asyncio
import time
import traceback
from typing import Optional

from api.endpoints.users import get_current_user, get_current_user_ws
from core.config import settings
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from schemas.game import GameEvent, GameView
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
            return await websocket.close(code=4000, reason="Already in a game")

        # Only add the user to the queue if they're not already in it
        if not await matchmaker.add_to_queue(websocket, current_user, ranked=False):
            return await websocket.close(code=4000, reason="Already in queue")

        while True:
            try:
                # Since manual disconnection doesn't fire the event, we have to manually check for disconnection
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                continue
            # Timeout means the WebSocket is still connected
            except asyncio.TimeoutError:
                # Try to find a match
                match = await matchmaker.get_random_player(2)

                if len(match) > 0:
                    ws1, player1 = match[0]
                    ws2, player2 = match[1]

                    # Get problems for the match
                    distribution = matchmaker.get_problem_distribution()
                    problems = await ProblemManager.get_problems_by_distribution(
                        db, distribution
                    )

                    # Create game and notify players
                    game_state = await game_manager.create_game(
                        player1, player2, problems, "unranked", db
                    )

                    match_data = {
                        "match_id": game_state.id,
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

                    break

                await asyncio.sleep(1)

    # Remove the user from the queue if they disconnect or some other error occurs
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
    """
    WebSocket endpoint for the ranked matchmaking queue

    :param websocket: WebSocket object
    :param current_user: User object
    :param db: Database session
    """

    try:
        # Check if the user is already in a game
        if game_manager.get_player_game(current_user.id):
            return await websocket.close(code=4000, reason="Already in a game")

        # Only add the user to the queue if they're not already in it
        if not await matchmaker.add_to_queue(websocket, current_user, ranked=True):
            return await websocket.close(code=4000, reason="Already in queue")

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                continue
            except asyncio.TimeoutError:
                # Try to find a ranked match
                match = await matchmaker.get_ranked_match()

                if match:
                    ws1, player1 = match[0]
                    ws2, player2 = match[1]

                    # Get problems based on average rating
                    avg_rating = (player1.rating + player2.rating) / 2
                    distribution = matchmaker.get_problem_distribution(
                        ranked=True, rating=avg_rating
                    )

                    problems = await ProblemManager.get_problems_by_distribution(
                        db, distribution
                    )

                    # Create game and notify players
                    game_state = await game_manager.create_game(
                        player1, player2, problems, "ranked", db
                    )

                    match_data = {
                        "match_id": game_state.id,
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

                    break

                await asyncio.sleep(1)

    except WebSocketDisconnect:
        await matchmaker.remove_from_queue(current_user.id)
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error in ranked queue websocket: {e}")
        await matchmaker.remove_from_queue(current_user.id)


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
        return await websocket.close(
            code=4000, reason="Game not found or already finished"
        )

    # Check if the user is a player in the game
    if current_user.id not in [game_state.player1.user_id, game_state.player2.user_id]:
        return await websocket.close(code=4000, reason="Not a player in this game")

    # Get the player state
    player = game_state.get_player_state(current_user.id)
    if not player:
        return await websocket.close(code=4000, reason="Player not found")

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

        # Send the current problem if the game is in progress
        if (
            game_state.status == GameStatus.IN_PROGRESS
            and player.current_problem_index < len(game_state.problems)
        ):
            current_problem = ProblemManager.prepare_problem_for_client(
                game_state.problems[player.current_problem_index]
            )
            await websocket.send_json({"type": "problem", "data": current_problem})

        # Start the game if both players are connected and the game is waiting
        opponent = game_state.get_opponent_state(current_user.id)
        if opponent and opponent.ws and game_state.status == GameStatus.WAITING:
            game_state.status = GameStatus.IN_PROGRESS

            problem = ProblemManager.prepare_problem_for_client(game_state.problems[0])

            await game_state.broadcast_event(GameEvent(type="game_start", data={}))

            await game_state.broadcast_event(GameEvent(type="problem", data=problem))

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                # No longer accept messages if the game is finished
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
                    await websocket.send_json(
                        {"type": "game_state", "data": game_view.model_dump()}
                    )
                # Handle player forfeits
                elif data["type"] == "forfeit":
                    await game_manager.forfeit_game(game_id, current_user.id)
                    await game_manager.handle_game_end(game_state, db)
                # Handle player submissions
                elif data["type"] == "submit":
                    # Check if the player is submitting too fast
                    current_time = time.time()
                    submission_cooldown = (
                        settings.SUBMISSION_COOLDOWN if not settings.TESTING else 2
                    )
                    if (
                        player.last_submission is not None
                        and current_time - player.last_submission < submission_cooldown
                    ):
                        await player.send_event(
                            GameEvent(
                                type="error",
                                data={
                                    "message": "You're submitting too fast. Please wait before submitting again"
                                },
                            )
                        )
                        continue

                    player.last_submission = current_time

                    # Execute the player's code on the hidden test cases
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

                    # Process the submission result
                    if result["success"]:
                        # Fetch deducted HP and whether the problem was solved
                        submission_result = await game_manager.process_submission(
                            game_id,
                            current_user.id,
                            result["summary"]["passed_tests"],
                            result["summary"]["total_tests"],
                        )

                        # Send the submission result to the player
                        await player.send_event(
                            GameEvent(
                                type="submission_result",
                                data={**result, **submission_result},
                            )
                        )

                        # Send the game state to both players
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

                        # Send the next problem if the current one was solved
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

                        # Check if the game has ended and handle it
                        if await game_manager.check_game_end(game_id):
                            await game_manager.handle_game_end(game_state, db)
                    else:
                        # Submission failed, send the result to the player
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


@router.get("/current-game", response_model=Optional[GameView])
async def get_current_game(
    current_user: User = Depends(get_current_user),
) -> Optional[GameView]:
    """
    Check if the user is in a game and return the game state. Used for reconnection.

    :param current_user: User object
    :return: GameView object if the user is in a game, None otherwise
    """
    game_state = game_manager.get_player_game(current_user.id)
    if game_state:
        return game_manager.create_game_view(game_state, current_user.id)
    return None
