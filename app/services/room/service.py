import asyncio
import random
import string
import time
from typing import Dict, List, Optional, Set

from core.config import settings
from db.models.user import User
from db.session import get_db
from fastapi import HTTPException, WebSocket
from services.room.state import RoomSettings, RoomState, RoomStatus, RoomView


class RoomService:
    """
    A service class that handles custom rooms
    """

    def __init__(self):
        self.rooms: Dict[str, RoomState] = {}
        self.lobby_connections: Set[WebSocket] = set()
        self.last_broadcast: float = 0
        self.pending_broadcast: bool = False

    def _generate_room_code(self) -> str:
        """
        Generate a unique room code

        :return: Room code
        """
        while True:
            code = code = "".join(
                random.choices(
                    string.ascii_uppercase + string.digits, k=settings.ROOM_CODE_LENGTH
                )
            )
            if code not in self.rooms:
                return code

    def _create_default_settings(self) -> RoomSettings:
        """
        Create default room settings

        :return: Room settings
        """
        easy, medium, hard = [
            float(x) for x in settings.DEFAULT_ROOM_SETTINGS["hp_multiplier"].split(",")
        ]
        prob_easy, prob_medium, prob_hard = [
            float(x)
            for x in settings.DEFAULT_ROOM_SETTINGS["problem_distribution"].split(",")
        ]

        return RoomSettings(
            problem_count=settings.DEFAULT_ROOM_SETTINGS["problem_count"],
            starting_hp=settings.DEFAULT_ROOM_SETTINGS["starting_hp"],
            base_hp_deduction=settings.DEFAULT_ROOM_SETTINGS["base_hp_deduction"],
            hp_multiplier_easy=easy,
            hp_multiplier_medium=medium,
            hp_multiplier_hard=hard,
            distribution_mode=settings.DEFAULT_ROOM_SETTINGS["distribution"],
            prob_easy=prob_easy,
            prob_medium=prob_medium,
            prob_hard=prob_hard,
            starting_sp=settings.STARTING_SP,
            starting_mp=settings.STARTING_MP,
            mana_recharge=settings.MANA_RECHARGE,
        )

    async def _get_user(self, user_id: int) -> User:
        """
        Get user from database

        :param user_id: User ID
        :return: User
        """
        # Get database session
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user
        finally:
            db.close()

    def _should_broadcast(self) -> bool:
        """
        Check if enough time has passed since the last broadcast

        :return: Whether to broadcast or not
        """
        current_time = time.time()
        return current_time - self.last_broadcast >= settings.ROOM_UPDATE_THROTTLE

    async def _send_room_list(self, ws: WebSocket):
        """
        Send room list to a single connection

        :param ws: WebSocket connection
        """
        room_list = await self._generate_room_list()

        try:
            await ws.send_json({"type": "room_list", "rooms": room_list})
        except:
            self.lobby_connections.discard(ws)
            raise

    async def _generate_room_list(self) -> List[Dict]:
        """
        Generate the room list data

        :return: List of room data
        """
        public_rooms = self.get_public_rooms()
        room_list = []

        for room in public_rooms:
            try:
                host = await self._get_user(room.host_id)
                room_list.append(
                    {
                        "room_code": room.room_code,
                        "host_name": host.username,
                        "host_display_name": host.display_name,
                        "settings": room.settings.model_dump(),
                        "player_count": 2 if room.guest_id else 1,
                    }
                )
            except:
                continue

        return room_list

    def create_room(
        self,
        host: User,
        is_public: bool = True,
        settings: Optional[RoomSettings] = None,
    ) -> RoomState:
        """
        Create a new room

        :param host: Host user
        :param is_public: Whether the room is public or private
        :param settings: Room settings

        :return: Room state
        """
        room_code = self._generate_room_code()

        room = RoomState(
            room_code=room_code,
            host_id=host.id,
            is_public=is_public,
            status=RoomStatus.WAITING,
            settings=settings or self._create_default_settings(),
        )

        self.rooms[room_code] = room

        if is_public:
            asyncio.create_task(self.broadcast_room_list())

        return room

    def get_room(self, room_code: str) -> Optional[RoomState]:
        """
        Get a room by room code

        :param room_code: Room code
        :return: Room state or None
        """
        return self.rooms.get(room_code)

    def remove_room(self, room_code: str):
        """
        Remove a room by room code

        :param room_code: Room code
        """
        room = self.rooms.get(room_code)
        if room and room.is_public:
            asyncio.create_task(self.broadcast_room_list())

        self.rooms.pop(room_code, None)

    def get_public_rooms(self) -> List[RoomState]:
        """
        Get all public rooms

        :return: List of public rooms
        """
        return [
            room
            for room in self.rooms.values()
            if room.is_public and room.status == RoomStatus.WAITING
        ]

    def create_room_view(self, room: RoomState, users: Dict[int, User]) -> RoomView:
        """
        Create a RoomView from RoomState

        :param room: Room state
        :param users: User dictionary

        :return: Room view
        """
        host = users[room.host_id]
        guest = users.get(room.guest_id) if room.guest_id else None

        return RoomView(
            room_code=room.room_code,
            host_name=host.username,
            host_display_name=host.display_name,
            guest_name=guest.username if guest else None,
            guest_display_name=guest.display_name if guest else None,
            is_public=room.is_public,
            status=room.status,
            settings=room.settings,
            host_ready=room.host_ready,
            guest_ready=room.guest_ready if room.guest_id else None,
        )

    async def add_lobby_connection(self, ws: WebSocket):
        """
        Add a new lobby connection and send initial room list

        :param ws: WebSocket
        """
        self.lobby_connections.add(ws)

        try:
            await self._send_room_list(ws)
        except:
            self.lobby_connections.remove(ws)

    async def remove_lobby_connection(self, ws: WebSocket):
        """
        Remove a lobby connection

        :param ws: WebSocket
        """
        self.lobby_connections.discard(ws)

    async def broadcast_room_list(self):
        """
        Broadcast the list of public rooms to all lobby connections if enough time has passed
        """
        if not self._should_broadcast():
            self.pending_broadcast = True
            return

        self.pending_broadcast = False
        self.last_broadcast = time.time()
        room_list = await self._generate_room_list()

        # Broadcast the room list to all lobby connections
        dead_connections = set()
        for ws in self.lobby_connections:
            try:
                await ws.send_json({"type": "room_list", "rooms": room_list})
            except:
                dead_connections.add(ws)

        # Remove dead connections
        self.lobby_connections -= dead_connections

    def is_user_in_any_room(self, user_id: int) -> bool:
        """
        Check if a user is in any room

        :param user_id: User ID
        :return: Whether the user is in any room
        """
        return any(room.is_player_in_room(user_id) for room in self.rooms.values())


room_service = RoomService()
