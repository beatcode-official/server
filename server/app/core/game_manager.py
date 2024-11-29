import json
import random
import time
import uuid
from typing import Dict, List

from core.challenge_manager import ChallengeManager
from core.websocket_manager import WebSocketManager
from services.docker_execution_service import DockerExecutionService


class GameManager:
    def __init__(
        self,
        challenge_manager: ChallengeManager,
        websocket_manager: WebSocketManager,
        docker_execution_service: DockerExecutionService,
    ):
        """
        Initializes the GameManager with the given ChallengeManager, WebSocketManager, and DockerExecutionService. This class manages the game logic and state.

        Args:
            challenge_manager (ChallengeManager): The ChallengeManager instance to use for managing challenges.
            websocket_manager (WebSocketManager): The WebSocketManager instance to use for managing WebSocket connections.
            docker_execution_service (DockerExecutionService): The DockerExecutionService instance to use for executing code.
        """
        self.challenge_manager = challenge_manager
        self.websocket_manager = websocket_manager
        self.docker_execution_service = docker_execution_service
        self.rooms: Dict[str, Dict] = {}
        self.challenge_fetch_limit = 2
        self.hp_per_test_case = 10

    def create_room(self, player_name: str) -> Dict[str, str]:
        """
        Creates a new room with the given player name as the host player.

        Args:
            player_name (str): The name of the host player.

        Returns:
            dict: A dictionary containing the room code and player ID of the host player.
        """
        room_code = self._generate_room_code()
        player_id = self._generate_player_id()
        self.rooms[room_code] = {
            "room_code": room_code,
            "room_status": "Waiting",
            "players": {
                player_id: [100, 0, 0]
            },  # [HP, Current Challenge Index, Solved Test Cases]
            "player_names": {player_id: player_name},
            "host_id": player_id,
            "start_time": None,
            "end_time": None,
            "challenge_ids": [],
        }
        return {"room_code": room_code, "player_id": player_id}

    def join_room(self, room_code: str, player_name: str) -> Dict[str, str]:
        """
        Joins an existing room with the given player name.

        Args:
            room_code (str): The room code of the room to join.
            player_name (str): The name of the player joining the room.

        Returns:
            dict: A dictionary containing the room code and player ID of the joined player.
        """
        if room_code not in self.rooms or len(self.rooms[room_code]["players"]) >= 2:
            raise ValueError("Invalid room code or room is full")

        player_id = self._generate_player_id()
        self.rooms[room_code]["players"][player_id] = [100, 0, 0]
        self.rooms[room_code]["player_names"][player_id] = player_name
        return {"room_code": room_code, "player_id": player_id}

    async def start_game(self, room_code: str, player_id: str):
        """
        Starts the game in the room with the given room code. Only the host player can start the game.

        Args:
            room_code (str): The room code of the room to start the game in.
            player_id (str): The player ID of the player starting the game.

        Raises:
            ValueError: If the player is not the host or if there are not enough players to start the game.
        """
        room = self.rooms[room_code]

        if room["host_id"] != player_id:
            raise ValueError("Only the host can start the game")

        if len(room["players"]) != 2:
            raise ValueError("Not enough players to start the game")

        room["room_status"] = "In-game"
        room["start_time"] = int(time.time())
        room["challenge_ids"] = self.challenge_manager.get_random_indexes(
            self.challenge_fetch_limit
        )

        await self._send_game_update(room_code)
        await self._send_new_challenge(room_code)

    async def submit_code(self, room_code: str, player_id: str, code: str):
        """
        Submits code for execution in the game.

        Args:
            room_code (str): The room code of the room where the game is being played.
            player_id (str): The player ID of the player submitting the code.
            code (str): The code to be executed.

        Raises:
            ValueError: If the game is not in progress.
        """
        room = self.rooms[room_code]
        if room["room_status"] != "In-game":
            raise ValueError("Game is not in progress")

        current_challenge_index = room["players"][player_id][1]
        challenge = self.challenge_manager.get_challenge(
            room["challenge_ids"][current_challenge_index]
        )

        result = self.docker_execution_service.execute_code(
            code,
            challenge["test_cases"],
            challenge["expected_outputs"],
            challenge["compare_func"],
        )

        await self._send_execution_results(room_code, player_id, result)

        if result["status"] == "success":
            opponent_id = next(
                pid for pid in room["players"].keys() if pid != player_id
            )
            new_passed_tests = result["passed_tests"] - room["players"][player_id][2]
            hp_deduction = min(
                new_passed_tests * self.hp_per_test_case,
                room["players"][opponent_id][0],
            )
            room["players"][opponent_id][0] -= hp_deduction
            room["players"][player_id][2] = result["passed_tests"]

            if result["passed_tests"] == len(challenge["test_cases"]):
                room["players"][player_id][1] += 1
                room["players"][player_id][
                    2
                ] = 0  # Reset solved test cases for the new challenge
                if room["players"][player_id][1] >= self.challenge_fetch_limit:
                    await self._end_game(room_code, player_id)
                else:
                    await self._send_new_challenge(room_code, player_id)

        await self._send_game_update(room_code)

    async def _send_game_update(self, room_code: str):
        """
        Sends a game update to all players in the room with the given room code.

        Args:
            room_code (str): The room code of the room to send the game update to.
        """
        room = self.rooms[room_code]
        player_ids = list(room["players"].keys())
        for i, player_id in enumerate(player_ids):
            opponent_id = player_ids[1 - i]
            update = {
                "event": "game_update",
                "event_data": {
                    "player1": {
                        "hp": room["players"][player_id][0],
                        "name": room["player_names"][player_id],
                        "current_challenge": room["players"][player_id][1] + 1,
                        "solved_test_cases": room["players"][player_id][2],
                    },
                    "player2": {
                        "hp": room["players"][opponent_id][0],
                        "name": room["player_names"][opponent_id],
                        "current_challenge": room["players"][opponent_id][1] + 1,
                        "solved_test_cases": room["players"][opponent_id][2],
                    },
                },
            }
            await self.websocket_manager.send(room_code, player_id, json.dumps(update))

    async def _send_new_challenge(self, room_code: str, player_id: str = None):
        """
        Sends a new challenge to the player with the given player ID in the room with the given room code. If no player ID is provided, the challenge is sent to all players in the room.

        Args:
            room_code (str): The room code of the room where the game is being played.
            player_id (str): The player ID of the player to send the new challenge to. If None, the challenge is sent to all players in the room.
        """
        room = self.rooms[room_code]
        if player_id is None:
            player_ids = list(room["players"].keys())
        else:
            player_ids = [player_id]

        for pid in player_ids:
            challenge_index = room["players"][pid][1]
            challenge = self.challenge_manager.get_challenge(
                room["challenge_ids"][challenge_index]
            )
            new_challenge = {
                "event": "new_challenge",
                "event_data": {
                    "challenge_info": {
                        "title": challenge["title"],
                        "description": challenge["description"],
                        "sample_test_cases": challenge["sample_test_cases"],
                        "sample_expected_output": challenge["sample_expected_outputs"],
                    }
                },
            }
            await self.websocket_manager.send(room_code, pid, json.dumps(new_challenge))

    async def _send_execution_results(
        self, room_code: str, player_id: str, result: Dict
    ):
        """
        Sends the results of code execution to the player with the given player ID in the room with the given room code.

        Args:
            room_code (str): The room code of the room where the game is being played.
            player_id (str): The player ID of the player to send the results to.
            result (dict): The results of the code execution.
        """
        execution_results = {
            "event": "execution_results",
            "event_data": {
                "passed": result["passed_tests"],
                "totalTestCases": len(
                    self.challenge_manager.get_challenge(
                        self.rooms[room_code]["challenge_ids"][
                            self.rooms[room_code]["players"][player_id][1]
                        ]
                    )["test_cases"]
                ),
            },
        }
        await self.websocket_manager.send(
            room_code, player_id, json.dumps(execution_results)
        )

    async def _end_game(self, room_code: str, winner_id: str):
        """
        Ends the game in the room with the given room code and declares the winner.

        Args:
            room_code (str): The room code of the room where the game is being played.
            winner_id (str): The player ID of the winner.
        """
        room = self.rooms[room_code]
        room["room_status"] = "Ended"
        room["end_time"] = int(time.time())

        end_game_message = {
            "event": "game_ended",
            "event_data": {"winner": room["player_names"][winner_id]},
        }
        await self.websocket_manager.broadcast(room_code, json.dumps(end_game_message))

    def _generate_room_code(self) -> str:
        """
        Generates a random room code.
        """
        return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))

    def _generate_player_id(self) -> str:
        """
        Generates a random player ID.
        """
        return uuid.uuid4().hex
