import asyncio
import time
import traceback

from api.endpoints.users.websockets import get_current_user_ws
from core.config import settings
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from schemas.game import GameEvent
from services.execution.service import code_execution
from services.game.state import GameState, GameStatus, PlayerState
from services.practice.constants import BOT_NAME
from services.practice.operator import PracticeGameOperator
from services.problem.service import ProblemManager
from sqlalchemy.orm import Session

router = APIRouter(prefix="/practice", tags=["practice"])
operator = PracticeGameOperator()


@router.websocket("")
async def practice_websocket(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for practice mode against a bot

    :param websocket: WebSocket object
    :param current_user: Current user
    :param db: Database session
    """
    distribution = {
        "easy": 1,
        "medium": 1,
        "hard": 1,
    }
    problems = await ProblemManager.get_problems_by_distribution(db, distribution)

    game_id = f"practice-{current_user.id}-{int(time.time())}"
    bot_id = -int(time.time())

    player = PlayerState(
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        rating=current_user.rating,
        ws=websocket,
    )

    bot_player = PlayerState(
        user_id=bot_id,
        username=BOT_NAME,
        display_name=BOT_NAME,
        rating=1000,
        ws=None,
    )

    game_state = GameState(
        id=game_id,
        player1=player,
        player2=bot_player,
        problems=problems,
        match_type="practice",
        status=GameStatus.WAITING,
        start_time=time.time(),
    )

    try:
        operator.register_game(game_state)
        game_view = operator.get_game_view(game_state, current_user.id)

        await websocket.send_json({"type": "game_state", "data": game_view})

        game_state.status = GameStatus.IN_PROGRESS
        await operator.create_bot(bot_id, bot_player, game_state)
        await operator.run_bot(game_id, current_user.display_name)

        if problems:
            problem = ProblemManager.prepare_problem_for_client(
                problems[0], explanation=True
            )
            await websocket.send_json({"type": "problem", "data": problem})

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                if game_state.status == GameStatus.FINISHED:
                    break

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
                    await operator.handle_chat_message(game_id)

                elif data["type"] == "change_bot_difficulty":
                    difficulty = data["data"]["difficulty"]
                    try:
                        await operator.change_bot_difficulty(game_id, difficulty)
                    except Exception as e:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "data": {
                                    "message": f"Failed to change bot difficulty: {str(e)}"
                                },
                            }
                        )

                elif data["type"] == "ability":
                    error = await operator.handle_ability_message(
                        game_state, current_user.id, data
                    )
                    if error:
                        await websocket.send_json(
                            {"type": "error", "data": {"message": error}}
                        )

                elif data["type"] == "query":
                    await websocket.send_json({"type": "game_state", "data": game_view})

                elif data["type"] == "forfeit":
                    game_state.status = GameStatus.FINISHED
                    game_state.winner = str(bot_id)
                    await game_state.broadcast_event(
                        GameEvent(
                            type="match_end",
                            data={
                                "winner": bot_player.username,
                                "winner_id": bot_id,
                                "reason": "forfeit",
                            },
                        )
                    )
                    break

                elif data["type"] == "retry":
                    await operator.cleanup_game(game_id)
                    new_bot_id = -int(time.time())
                    new_game_id = f"practice-{current_user.id}-{new_bot_id}"

                    player = PlayerState(
                        user_id=current_user.id,
                        username=current_user.username,
                        display_name=current_user.display_name,
                        rating=current_user.rating,
                        ws=websocket,
                    )

                    new_bot_player = PlayerState(
                        user_id=new_bot_id,
                        username=BOT_NAME,
                        display_name=BOT_NAME,
                        rating=1000,
                        ws=None,
                    )

                    game_state = GameState(
                        id=new_game_id,
                        player1=player,
                        player2=new_bot_player,
                        problems=await ProblemManager.get_problems_by_distribution(
                            db, distribution
                        ),
                        match_type="practice",
                        status=GameStatus.WAITING,
                        start_time=time.time(),
                    )

                    game_view = operator.get_game_view(game_state, current_user.id)
                    await websocket.send_json({"type": "game_state", "data": game_view})

                    game_state.status = GameStatus.IN_PROGRESS
                    await operator.create_bot(new_bot_id, bot_player, game_state)
                    await operator.run_bot(new_game_id, current_user.display_name)

                    if game_state.problems:
                        problem = ProblemManager.prepare_problem_for_client(
                            game_state.problems[0]
                        )
                        await websocket.send_json({"type": "problem", "data": problem})

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
                    lang = data["data"]["lang"]
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
                        submission_result = await operator.process_submission(
                            game_id,
                            current_user.id,
                            result["summary"]["passed_tests"],
                            result["summary"]["total_tests"],
                        )

                        await operator.heal_bot_if_needed(game_id, bot_player)
                        await player.send_event(
                            GameEvent(
                                type="submission_result",
                                data={**result, **submission_result},
                            )
                        )

                        await game_state.player1.send_event(
                            GameEvent(
                                type="game_state",
                                data=operator.get_game_view(
                                    game_state, game_state.player1.user_id
                                ),
                            )
                        )

                        await game_state.player2.send_event(
                            GameEvent(
                                type="game_state",
                                data=operator.get_game_view(
                                    game_state, game_state.player2.user_id
                                ),
                            )
                        )

                        game_view = operator.get_game_view(game_state, current_user.id)

                        await websocket.send_json(
                            {"type": "game_state", "data": game_view}
                        )

                        if (
                            submission_result["problem_solved"]
                            and problem_index < len(game_state.problems) - 1
                        ):
                            player.current_problem_index += 1
                            next_problem = ProblemManager.prepare_problem_for_client(
                                problems[player.current_problem_index]
                            )
                            await websocket.send_json(
                                {"type": "problem", "data": next_problem}
                            )

                            if bot_player.hp <= 0:
                                game_state.status = GameStatus.FINISHED
                                game_state.winner = current_user.id
                                await game_state.broadcast_event(
                                    GameEvent(
                                        type="match_end",
                                        data={
                                            "winner": current_user.username,
                                            "winner_id": current_user.id,
                                            "reason": "hp_depleted",
                                        },
                                    )
                                )
                                break
                    else:
                        await websocket.send_json(
                            {"type": "submission_result", "data": result}
                        )

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                try:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {"message": f"An error occurred: {str(e)}"},
                        }
                    )
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except RuntimeError:
        pass
    except Exception:
        print(f"Error in practice websocket: {traceback.format_exc()}")
    finally:
        await operator.cleanup_game(game_id)
        game_state.status = GameStatus.FINISHED
