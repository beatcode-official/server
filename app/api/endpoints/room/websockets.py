import asyncio
import time
import traceback

from api.endpoints.users.websockets import get_current_user_ws
from api.endpoints.room.utils import get_users_from_db
from core.errors.room import (
    WSRoomNotFoundError,
    WSRoomFullError,
    WSAlreadyInRoomError,
    RoomError,
    GuestStartGameError,
    NotAllPlayersReadyError,
    NotEnoughPlayersError,
)
from db.models.user import User
from db.session import get_db
from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from services.game.manager import game_manager
from services.room.service import room_service
from services.room.state import RoomStatus
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.websocket("/lobby")
async def room_lobby_websocket(
    websocket: WebSocket, current_user: User = Depends(get_current_user_ws)
):
    """
    WebSocket endpoint for room lobby

    :param websocket: WebSocket connection
    :param current_user: Current user
    """
    try:
        await room_service.add_lobby_connection(websocket)

        while True:
            try:
                # Keep connection alive
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    finally:
        await room_service.remove_lobby_connection(websocket)


@router.websocket("/{room_code}")
async def room_websocket(
    websocket: WebSocket,
    room_code: str,
    current_user: User = Depends(get_current_user_ws),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for room management

    :param websocket: WebSocket connection
    :param room_code: Room code
    :param current_user: Current user
    :param db: Database session
    """
    room = room_service.get_room(room_code)
    if not room:
        raise WSRoomNotFoundError()

    # Handle user joining the room
    if room.is_player_in_room(current_user.id):
        # Reconnection case
        if current_user.id == room.host_id:
            room.host_ws = websocket
        else:
            room.guest_ws = websocket
    elif room.is_full():
        raise WSRoomFullError()
    else:
        # New guest joining the room
        await _handle_guest_join(room, room_service, current_user, websocket)

    try:
        await _broadcast_room_state(room, room_service, db)
        await _run_room_loop(room, room_service, current_user, websocket, db)
    finally:
        # Clean up when a player disconnects
        room.remove_player(current_user.id)

        if room.host_id is None:
            # Room is empty, remove it
            was_public = room.is_public
            room_service.remove_room(room_code)
            if was_public:
                asyncio.create_task(room_service.broadcast_room_list())

        else:
            await _broadcast_room_state(room, room_service, db)

async def _handle_guest_join(room, room_service, current_user, websocket):
    # Check if user is already in any room (except this one)
    if room_service.is_user_in_any_room(current_user.id) and not room.is_player_in_room(
        current_user.id
    ):
        raise WSAlreadyInRoomError()

    room.guest_id = current_user.id
    room.guest_ws = websocket

    # Trigger room update when new player joins
    if room.is_public:
        asyncio.create_task(room_service.broadcast_room_list())


async def _broadcast_room_state(room, room_service, db):
    users = get_users_from_db(room, db)
    # Broadcast updated room state to all players
    await room.broadcast(
        {
            "type": "room_state",
            "data": room_service.create_room_view(room, users).model_dump(),
        }
    )

    if room.is_public:
        await room_service.broadcast_room_list()


async def _run_room_loop(room, room_service, current_user, websocket, db):
    while True:
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
            # If data received, update users
            users = get_users_from_db(room, db)
            await _handle_messages(room, data, users, current_user, websocket, db)
        except asyncio.TimeoutError:
            continue
        except RoomError as e:
            await e.send_json(websocket)
            continue
        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"Error in room websocket")
            print(traceback.format_exc())
            break


async def _handle_messages(room, data, users, current_user, websocket, db):
    if data["type"] == "toggle_ready":
        await _handle_toggle_ready(room, data, users, current_user, websocket)

    elif data["type"] == "start_game":
        await _handle_start_game(room, data, users, current_user, websocket, db)

    elif data["type"] == "chat":
        # Broadcast chat message
        await room.broadcast(
            {
                "type": "chat",
                "data": {
                    "sender": current_user.username,
                    "message": data["data"]["message"],
                    "timestamp": time.time(),
                },
            }
        )


async def _handle_toggle_ready(room, data, users, current_user, websocket):
    # Toggle ready status
    current_ready = room.get_player_ready(current_user.id)
    room.set_player_ready(current_user.id, not current_ready)

    # Broadcast updated room state
    await room.broadcast(
        {
            "type": "room_state",
            "data": room_service.create_room_view(room, users).model_dump(),
        }
    )


async def _handle_start_game(room, data, users, current_user, websocket, db):
    if current_user.id != room.host_id:
        raise GuestStartGameError()

    if not room.is_full():
        raise NotEnoughPlayersError()

    if not room.are_players_ready():
        raise NotAllPlayersReadyError()

    # Create game with room settings
    game_state = await game_manager.create_game_with_settings(
        users[room.host_id], users[room.guest_id], room.settings, db
    )

    room.status = RoomStatus.IN_GAME
    room.game_id = game_state.id
    room.reset_ready_status()

    # Notify players
    await room.broadcast({"type": "game_started", "data": {"game_id": game_state.id}})
