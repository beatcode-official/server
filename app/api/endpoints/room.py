import asyncio
import time
from typing import Optional

from api.endpoints.users import get_current_user, get_current_user_ws
from db.models.user import User
from db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect, status)
from services.game.manager import game_manager
from services.room.service import room_service
from services.room.state import RoomSettings, RoomStatus
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/create")
async def create_room(
    is_public: bool = True,
    settings: Optional[RoomSettings] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new room

    :param is_public: Whether the room is public or private
    :param settings: Room settings
    :param current_user: Current user

    :return: Room code
    """
    # Check if user is already in a room or game
    for room in room_service.rooms.values():
        if room.is_player_in_room(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already in a room"
            )

    if game_manager.get_player_game(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already in a game"
        )

    room = room_service.create_room(current_user, is_public, settings)
    return {"room_code": room.room_code}


@router.get("/{room_code}")
async def get_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get room information

    :param room_code: Room code
    :param current_user: Current user
    :param db: Database session

    :return: Room information
    """
    room = room_service.get_room(room_code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    users = {}
    users[room.host_id] = db.query(User).filter(User.id == room.host_id).first()
    if room.guest_id:
        users[room.guest_id] = db.query(User).filter(User.id == room.guest_id).first()

    return room_service.create_room_view(room, users)


@router.patch("/{room_code}/settings")
async def update_room_settings(
    room_code: str,
    settings: RoomSettings,
    current_user: User = Depends(get_current_user)
):
    """
    Update room settings (host only)

    :param room_code: Room code
    :param settings: Room settings
    :param current_user: Current user

    :return: Success message
    """
    room = room_service.get_room(room_code)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )

    if room.host_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can update room settings"
        )

    if room.status != RoomStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify room settings while game is in progress"
        )

    room.settings = settings
    await room.broadcast({
        "type": "settings_updated",
        "data": settings.model_dump()
    })

    if room.is_public:
        asyncio.create_task(room_service.handle_room_update())

    return {"message": "Settings updated successfully"}


@router.websocket("/lobby")
async def room_lobby_websocket(
    websocket: WebSocket,
    current_user: User = Depends(get_current_user_ws)
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
    db: Session = Depends(get_db)
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
        return await websocket.close(code=4004, reason="Room not found")

    # Handle user joining the room
    if room.is_player_in_room(current_user.id):
        # Reconnection case
        if current_user.id == room.host_id:
            room.host_ws = websocket
        else:
            room.guest_ws = websocket
    elif room.is_full():
        return await websocket.close(code=4003, reason="Room is full")
    else:
        # New guest joining the room

        # Check if user is already in any room (except this one)
        if room_service.is_user_in_any_room(current_user.id) and not room.is_player_in_room(current_user.id):
            return await websocket.close(code=4005, reason="Already in another room")

        room.guest_id = current_user.id
        room.guest_ws = websocket

        # Trigger room update when new player joins
        if room.is_public:
            asyncio.create_task(room_service.handle_room_update())

    try:
        # Get users for the room view
        users = {}
        users[room.host_id] = db.query(User).filter(User.id == room.host_id).first()
        if room.guest_id:
            users[room.guest_id] = db.query(User).filter(User.id == room.guest_id).first()

        # Broadcast updated room state to all players
        await room.broadcast({
            "type": "room_state",
            "data": room_service.create_room_view(room, users).model_dump()
        })

        if room.is_public:
            await room_service.broadcast_room_list()

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)

                if data["type"] == "toggle_ready":
                    # Toggle ready status
                    current_ready = room.get_player_ready(current_user.id)
                    room.set_player_ready(current_user.id, not current_ready)

                    # Broadcast updated room state
                    users = {
                        room.host_id: db.query(User).filter(User.id == room.host_id).first()
                    }
                    if room.guest_id:
                        users[room.guest_id] = db.query(User).filter(
                            User.id == room.guest_id
                        ).first()

                    await room.broadcast({
                        "type": "room_state",
                        "data": room_service.create_room_view(room, users).model_dump()
                    })

                elif data["type"] == "start_game":
                    if current_user.id != room.host_id:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Only the host can start the game"}
                        })
                        continue

                    if not room.is_full():
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Need 2 players to start"}
                        })
                        continue

                    if not room.are_players_ready():
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "All players must be ready to start"}
                        })
                        continue

                    # Create game with room settings
                    game_state = await game_manager.create_game_with_settings(
                        users[room.host_id],
                        users[room.guest_id],
                        room.settings,
                        db
                    )

                    room.status = RoomStatus.IN_GAME
                    room.game_id = game_state.id
                    room.reset_ready_status()

                    # Notify players
                    await room.broadcast({
                        "type": "game_started",
                        "data": {"game_id": game_state.id}
                    })

                elif data["type"] == "chat":
                    # Broadcast chat message
                    await room.broadcast({
                        "type": "chat",
                        "data": {
                            "sender": current_user.username,
                            "message": data["data"]["message"],
                            "timestamp": time.time()
                        }
                    })

            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error in room websocket: {e}")
                break

    finally:
        # Clean up when a player disconnects
        room.remove_player(current_user.id)

        if room.host_id is None:
            # Room is empty, remove it
            was_public = room.is_public
            room_service.remove_room(room_code)
            if was_public:
                asyncio.create_task(room_service.handle_room_update())

        else:
            # Broadcast updated room state
            users = {room.host_id: db.query(User).filter(User.id == room.host_id).first()}
            if room.guest_id:
                users[room.guest_id] = db.query(User).filter(User.id == room.guest_id).first()

            await room.broadcast({
                "type": "room_state",
                "data": room_service.create_room_view(room, users).model_dump()
            })

            if room.is_public:
                asyncio.create_task(room_service.handle_room_update())
