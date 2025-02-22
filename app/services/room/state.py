from enum import Enum
from typing import Dict, Literal, Optional

from fastapi import WebSocket
from pydantic import BaseModel, field_validator


class RoomStatus(str, Enum):
    """
    Enum for room status
    """

    WAITING = "waiting"
    IN_GAME = "in_game"


class RoomSettings(BaseModel):
    """
    Model for room settings

    :param problem_count: Number of problems in the room
    :param starting_hp: Starting HP of the players
    :param base_hp_deduction: Base HP deduction per test case
    :param hp_multiplier_easy: HP multiplier for easy problems
    :param hp_multiplier_medium: HP multiplier for medium problems
    :param hp_multiplier_hard: HP multiplier for hard problems
    :param distribution_mode: Problem difficulty distribution mode
    :param prob_easy: Probability of an easy problem
    :param prob_medium: Probability of a medium problem
    :param prob_hard: Probability of a hard problem
    """

    problem_count: int
    starting_hp: int
    base_hp_deduction: int
    hp_multiplier_easy: float
    hp_multiplier_medium: float
    hp_multiplier_hard: float
    distribution_mode: Literal["auto", "fixed"]
    prob_easy: float
    prob_medium: float
    prob_hard: float
    starting_sp: int
    starting_mp: int
    mana_recharge: int

    @field_validator("problem_count")
    def validate_problem_count(cls, v):
        min_count, max_count = 1, 10
        if not (min_count <= v <= max_count):
            raise ValueError(
                f"Problem count must be between {min_count} and {max_count}"
            )
        return v

    @field_validator("starting_hp")
    def validate_starting_hp(cls, v):
        min_hp, max_hp = 1, 1000
        if not (min_hp <= v <= max_hp):
            raise ValueError(f"Starting HP must be between {min_hp} and {max_hp}")
        return v

    @field_validator("base_hp_deduction")
    def validate_base_hp_deduction(cls, v):
        min_deduction, max_deduction = 1, 100
        if not (min_deduction <= v <= max_deduction):
            raise ValueError(
                f"Base HP deduction must be between {min_deduction} and {max_deduction}"
            )
        return v

    @field_validator("hp_multiplier_easy", "hp_multiplier_medium", "hp_multiplier_hard")
    def validate_hp_multiplier(cls, v):
        min_multiplier, max_multiplier = 0.1, 10.0
        if not (min_multiplier <= v <= max_multiplier):
            raise ValueError(
                f"HP multiplier must be between {min_multiplier} and {max_multiplier}"
            )
        return v

    @field_validator("prob_easy", "prob_medium", "prob_hard")
    def validate_prob(cls, v):
        min_prob, max_prob = 0.0, 3.0
        if not (min_prob <= v <= max_prob):
            raise ValueError(f"Probability must be between {min_prob} and {max_prob}")
        return v

    # @field_validator("prob_hard")
    # def validate_prob_sum(cls, v, info):
    #     values = info.data
    #     if "prob_easy" in values and "prob_medium" in values:
    #         total = values["prob_easy"] + values["prob_medium"] + v
    #         if not (0.99 <= total <= 1.01):  # Allow small floating point errors
    #             raise ValueError("Probabilities must sum to 1")
    #     return v

    @field_validator("starting_sp")
    def validate_starting_sp(cls, v):
        min_sp, max_sp = 0, 1000
        if not (min_sp <= v <= max_sp):
            raise ValueError(f"Starting SP must be between {min_sp} and {max_sp}")
        return v

    @field_validator("starting_mp")
    def validate_starting_mp(cls, v):
        min_mp, max_mp = 0, 1000
        if not (min_mp <= v <= max_mp):
            raise ValueError(f"Starting MP must be between {min_mp} and {max_mp}")
        return v

    @field_validator("mana_recharge")
    def validate_mana_recharge(cls, v):
        min_recharge, max_recharge = 0, 500
        if not (min_recharge <= v <= max_recharge):
            raise ValueError(
                f"Mana recharge must be between {min_recharge} and {max_recharge}"
            )
        return v


class RoomState(BaseModel):
    """
    A model for the state of a room

    :param room_code: Room code
    :param host_id: Host user ID
    :param is_public: Whether the room is public
    :param status: Room status
    :param settings: Room settings
    :param game_id: Game ID if the room is in game
    :param host_ready: Whether the host is ready
    :param guest_ready: Whether the guest is ready
    :param host_ws: Host websocket
    :param guest_ws: Guest websocket
    :param guest_id: Guest user ID
    """

    room_code: str
    host_id: int
    is_public: bool
    status: RoomStatus
    settings: RoomSettings
    game_id: Optional[str] = None
    host_ready: bool = False
    guest_ready: bool = False

    # Not included in model serialization
    host_ws: Optional[WebSocket] = None
    guest_ws: Optional[WebSocket] = None
    guest_id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

    def is_full(self) -> bool:
        """
        Check if room has 2 players
        """
        return self.guest_id is not None

    def is_player_in_room(self, user_id: int) -> bool:
        """
        Check if a user is in the room
        """
        return user_id in [self.host_id, self.guest_id]

    def are_players_ready(self) -> bool:
        """
        Check if both players are ready

        :return: Whether both players are ready
        """
        return self.is_full() and self.host_ready and self.guest_ready

    def get_player_ready(self, user_id: int) -> bool:
        """
        Get player ready status

        :param user_id: User ID
        :return: Ready status
        """
        if user_id == self.host_id:
            return self.host_ready
        elif user_id == self.guest_id:
            return self.guest_ready
        return False

    def set_player_ready(self, user_id: int, ready: bool = True):
        """
        Set player ready status

        :param user_id: User ID
        :param ready: Ready status
        """
        if user_id == self.host_id:
            self.host_ready = ready
        elif user_id == self.guest_id:
            self.guest_ready = ready

    def reset_ready_status(self):
        """
        Reset ready status of all players
        """
        self.host_ready = False
        self.guest_ready = False

    def get_player_ws(self, user_id: int) -> Optional[WebSocket]:
        """
        Get the websocket of a player
        """
        if user_id == self.host_id:
            return self.host_ws
        elif user_id == self.guest_id:
            return self.guest_ws
        return None

    def remove_player(self, user_id: int):
        """
        Remove a player from the room
        """
        if user_id == self.guest_id:
            self.guest_id = None
            self.guest_ws = None
        elif user_id == self.host_id:
            # If host leaves, make guest the new host if there is one
            if self.guest_id:
                self.host_id = self.guest_id
                self.host_ws = self.guest_ws
                self.guest_id = None
                self.guest_ws = None
            else:
                self.host_id = None
                self.host_ws = None

    async def broadcast(self, message: Dict):
        """
        Broadcast a message to all players in the room
        """
        if self.host_ws:
            try:
                await self.host_ws.send_json(message)
            except:
                self.host_ws = None

        if self.guest_ws:
            try:
                await self.guest_ws.send_json(message)
            except:
                self.guest_ws = None


class RoomView(BaseModel):
    """
    A model for room data to be sent to clients

    :param room_code: Room code
    :param host_name: Host username
    :param host_display_name: Host display name
    :param guest_name: Guest username
    :param guest_display_name: Guest display name
    :param is_public: Whether the room is public
    :param status: Room status
    :param settings: Room settings
    :param host_ready: Whether the host is ready
    :param guest_ready: Whether the guest is ready
    """

    room_code: str
    host_name: str
    host_display_name: str
    guest_name: Optional[str]
    guest_display_name: Optional[str]
    is_public: bool
    status: RoomStatus
    settings: RoomSettings
    host_ready: bool
    guest_ready: Optional[bool]
