import asyncio
import random
import time
import traceback

from api.endpoints.users.websockets import get_current_user_ws
from core.config import settings
from db.models.user import User
from db.session import get_db
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from schemas.game import GameEvent
from services.execution.service import code_execution
from services.game.ability import ability_manager
from services.game.state import GameState, GameStatus, PlayerState
from services.practice.bot import HEALING_THRESHOLD, practice_bot_manager
from services.practice.dialogue import (
    get_ability_received_dialogue,
)
from services.practice.manager import practice_game_manager
from services.problem.service import ProblemManager
from sqlalchemy.orm import Session

router = APIRouter(prefix="/practice", tags=["practice"])


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
    # Fetch problems
    distribution = {
        "easy": 1,
        "medium": 1,
        "hard": 1,
    }  # Simple distribution for practice
    problems = await ProblemManager.get_problems_by_distribution(db, distribution)

    # Create game state with a bot opponent
    bot_id = -int(
        time.time()
    )  # Use a negative number to ensure uniqueness but still provide an integer
    game_id = f"practice-{current_user.id}-{int(time.time())}"

    # Create player states
    player = PlayerState(
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        rating=current_user.rating,
        ws=websocket,
    )

    bot_player = PlayerState(
        user_id=bot_id,
        username=practice_bot_manager.get_bot_name(),
        display_name=practice_bot_manager.get_bot_name(),
        rating=1000,  # Default rating for bot
        ws=None,  # Bot doesn't need a websocket
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

    practice_bot_manager.create_bot(bot_id, bot_player, game_state)

    try:
        game_view = practice_game_manager.create_game_view(
            game_state, current_user.id
        ).model_dump()

        await websocket.send_json({"type": "game_state", "data": game_view})

        # Start the game
        game_state.status = GameStatus.IN_PROGRESS

        # Send first problem
        if problems:
            problem = ProblemManager.prepare_problem_for_client(
                problems[0], explanation=True
            )
            await websocket.send_json({"type": "problem", "data": problem})

            await practice_bot_manager.start_bot_simulation(
                game_id, current_user.display_name
            )

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                # No longer accept messages if the game is finished
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
                    await practice_bot_manager.get_chat_response(game_id)

                elif data["type"] == "change_bot_difficulty":
                    difficulty = data["data"]["difficulty"]
                    if difficulty in ["easy", "medium", "hard"]:
                        success = await practice_bot_manager.change_bot_difficulty(
                            game_id, difficulty
                        )
                        if not success:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "data": {
                                        "message": "Failed to change bot difficulty"
                                    },
                                }
                            )
                    else:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "data": {
                                    "message": "Invalid difficulty level. Valid options are: easy, medium, hard"
                                },
                            }
                        )

                elif data["type"] == "ability":
                    action = data["data"].get("action", "")
                    ability_id = data["data"].get("ability_id", "")

                    error = await ability_manager.handle_ability_message(
                        game_state, practice_game_manager, current_user.id, data["data"]
                    )
                    if error:
                        await websocket.send_json(
                            {"type": "error", "data": {"message": error}}
                        )
                    else:
                        if action == "use" and ability_id != "healio":
                            bot_response = get_ability_received_dialogue()
                            await game_state.broadcast_event(
                                GameEvent(
                                    type="chat",
                                    data={
                                        "sender": bot_player.username,
                                        "message": bot_response,
                                        "timestamp": time.time(),
                                    },
                                )
                            )

                        game_view = practice_game_manager.create_game_view(
                            game_state, current_user.id
                        ).model_dump()

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
                    practice_bot_manager.cleanup_bot(game_id)
                    new_bot_id = -int(time.time())
                    new_game_id = f"practice-{current_user.id}-{int(time.time())}"

                    # Start new game
                    player = PlayerState(
                        user_id=current_user.id,
                        username=current_user.username,
                        display_name=current_user.display_name,
                        rating=current_user.rating,
                        ws=websocket,
                    )

                    # Create new bot player
                    new_bot_player = PlayerState(
                        user_id=new_bot_id,
                        username=practice_bot_manager.get_bot_name(),
                        display_name=practice_bot_manager.get_bot_name(),
                        rating=1000,
                        ws=None,
                    )

                    # Create new game state
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

                    # Create new bot
                    practice_bot_manager.create_bot(
                        new_bot_id, new_bot_player, game_state
                    )

                    # Send new game state to player
                    game_view = practice_game_manager.create_game_view(
                        game_state, current_user.id
                    ).model_dump()

                    await websocket.send_json({"type": "game_state", "data": game_view})

                    # Start new game
                    game_state.status = GameStatus.IN_PROGRESS

                    if game_state.problems:
                        problem = ProblemManager.prepare_problem_for_client(
                            game_state.problems[0]
                        )
                        await websocket.send_json({"type": "problem", "data": problem})

                        await practice_bot_manager.start_bot_simulation(
                            new_game_id, current_user.display_name
                        )

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
                        passed_tests = result["summary"]["passed_tests"]
                        total_tests = result["summary"]["total_tests"]

                        damage = int((passed_tests / total_tests) * 30)
                        problem_solved = passed_tests == total_tests

                        bot_hp_before = bot_player.hp

                        bot_player.hp = max(0, bot_player.hp - damage)

                        active_bot = practice_bot_manager.active_bots.get(str(game_id))

                        if (
                            active_bot
                            and bot_player.hp < HEALING_THRESHOLD
                            and bot_hp_before >= HEALING_THRESHOLD
                            and "healio" in bot_player.abilities
                        ):
                            await asyncio.sleep(random.randint(1, 5))
                            healio = ability_manager.abilities.get("healio")
                            if healio and bot_player.mana_points >= healio.mp_cost:
                                asyncio.create_task(active_bot.trigger_bot_healing())

                            if problem_solved:
                                player.mana_points += (
                                    settings.MANA_RECHARGE
                                    if hasattr(settings, "MANA_RECHARGE")
                                    else 50
                                )

                        submission_result = {
                            "damage_dealt": damage,
                            "problem_solved": problem_solved,
                        }

                        # Send submission result to player
                        await websocket.send_json(
                            {
                                "type": "submission_result",
                                "data": {**result, **submission_result},
                            }
                        )

                        game_view = practice_game_manager.create_game_view(
                            game_state, current_user.id
                        ).model_dump()

                        await websocket.send_json(
                            {"type": "game_state", "data": game_view}
                        )

                        # Move to next problem if current one is solved
                        if problem_solved and problem_index < len(problems) - 1:
                            player.current_problem_index += 1
                            next_problem = ProblemManager.prepare_problem_for_client(
                                problems[player.current_problem_index]
                            )
                            await websocket.send_json(
                                {"type": "problem", "data": next_problem}
                            )

                        if bot_player.hp <= 0:
                            game_state.status = GameStatus.FINISHED
                            game_state.winner_id = current_user.id
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
        # Clean up the bot through the manager
        practice_bot_manager.cleanup_bot(game_id)
        game_state.status = GameStatus.FINISHED
