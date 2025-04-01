import asyncio
from typing import Optional

from api.endpoints.users.controller import get_current_user
from api.endpoints.room.utils import get_users_from_db
from core.errors.room import (
    RoomNotFoundError,
    GuestUpdateSettingsError,
    AlreadyInRoomError,
    GameInProgressError,
)
from core.errors.game import AlreadyInGameError
from db.models.user import User
from db.session import get_db
from fastapi import (
    APIRouter,
    Depends,
)
from services.game.manager import game_manager
from services.room.service import room_service
from services.room.state import RoomSettings, RoomStatus
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/create")
async def create_room(
    is_public: bool = True,
    settings: Optional[RoomSettings] = None,
    current_user: User = Depends(get_current_user),
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
            raise AlreadyInRoomError()

    if game_manager.get_player_game(current_user.id):
        raise AlreadyInGameError()

    room = room_service.create_room(current_user, is_public, settings)
    return {"room_code": room.room_code}


@router.get("/{room_code}")
async def get_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        raise RoomNotFoundError()

    users = get_users_from_db(room, db)
    return room_service.create_room_view(room, users)


@router.patch("/{room_code}/settings")
async def update_room_settings(
    room_code: str,
    settings: RoomSettings,
    current_user: User = Depends(get_current_user),
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
        raise RoomNotFoundError()

    if room.host_id != current_user.id:
        raise GuestUpdateSettingsError()
    if room.status != RoomStatus.WAITING:
        raise GameInProgressError()

    room.settings = settings
    await room.broadcast({"type": "settings_updated", "data": settings.model_dump()})

    if room.is_public:
        asyncio.create_task(room_service.broadcast_room_list())

    return {"message": "Settings updated successfully"}
