import json
import os
import subprocess
import sys
import time
from pprint import pprint

from websockets.exceptions import ConnectionClosedError
from websockets.legacy.exceptions import InvalidStatusCode

# fmt: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from core.config import settings
from tests.integration.functions import *

# fmt: on

# Important: Make sure server is in test mode.
assert settings.TESTING, "Server is not in testing mode"
# Clear database before hand with "python -m db.init --droptest"
subprocess.run(["python", "-m", "db.init", "--droptest"], stdout=subprocess.DEVNULL)

# Global Variables
SKIP = []
print(f"Skipping tests: {SKIP}")

# Test 1
if 1 not in SKIP:
    print("Running test 1: Room Creation Tests", end=" ", flush=True)

    async def test1():
        auth_headers1 = await make_user(
            "rtest1", "rtest1@email.com", "password", "RTester 1"
        )
        auth_headers2 = await make_user(
            "rtest2", "rtest2@email.com", "password", "RTester 2"
        )

        session = requests.Session()

        # Test: Create room normally
        room_data = await create_room(auth_headers1, session)
        assert "room_code" in room_data

        # Test: Create room while in room
        room_data2 = await create_room(auth_headers1, session)
        assert "detail" in room_data2 and room_data2["detail"] == "Already in a room"

        await leave_room(room_data["room_code"], auth_headers1)

        # Test: Create room with custom settings
        custom_settings = {
            "problem_count": 5,
            "starting_hp": 200,
            "base_hp_deduction": 4,
            "hp_multiplier_easy": 1.5,
            "hp_multiplier_medium": 2.0,
            "hp_multiplier_hard": 2.5,
            "distribution_mode": "fixed",
            "prob_easy": 0.4,
            "prob_medium": 0.3,
            "prob_hard": 0.3,
            "starting_sp": 200,
            "starting_mp": 200,
            "mana_recharge": 50,
        }
        room_data3 = await create_room(auth_headers2, session, settings=custom_settings)
        assert "room_code" in room_data3

        await leave_room(room_data3["room_code"], auth_headers2)

        # Test: Create room with invalid settings
        invalid_settings = {
            "problem_count": 0,  # Invalid value
            "starting_hp": 200,
            "base_hp_deduction": 4,
            "hp_multiplier_easy": 1.5,
            "hp_multiplier_medium": 2.0,
            "hp_multiplier_hard": 2.5,
            "distribution_mode": "fixed",
            "prob_easy": 0.4,
            "prob_medium": 0.3,
            "prob_hard": 0.3,
            "starting_sp": 200,
            "starting_mp": 200,
            "mana_recharge": 50,
        }
        try:
            await create_room(auth_headers2, session, settings=invalid_settings)
            assert False
        except Exception:
            pass

        # Test: Create private room
        private_room = await create_room(auth_headers2, session, is_public=False)
        assert "room_code" in private_room

        await leave_room(private_room["room_code"], auth_headers2)

    asyncio.run(test1())

    print("✅")

# Test 2: Room Fetching Tests
if 2 not in SKIP:
    print("Running test 2: Room Fetching Tests", end=" ", flush=True)

    async def test2():
        auth_headers = await make_user(
            "rtest3", "rtest3@email.com", "password", "RTester 3"
        )
        session = requests.Session()

        # Create a room
        room_data = await create_room(auth_headers, session)
        room_code = room_data["room_code"]

        # Test: Fetch existing room
        room_info = await get_room(room_code, auth_headers)
        assert room_info["room_code"] == room_code
        assert room_info["host_name"] == "rtest3"

        # Test: Fetch non-existent room
        room_info = await get_room("INVALID", auth_headers)
        assert "detail" in room_info and room_info["detail"] == "Room not found"

        await leave_room(room_code, auth_headers)

    asyncio.run(test2())
    print("✅")

# Test 3: Room Settings Update Tests
if 3 not in SKIP:
    print("Running test 3: Room Settings Update Tests", end=" ", flush=True)

    async def test3():
        auth_headers1 = await make_user(
            "rtest4", "rtest4@email.com", "password", "RTester 4"
        )
        auth_headers2 = await make_user(
            "rtest5", "rtest5@email.com", "password", "RTester 5"
        )
        session = requests.Session()

        # Create a room
        room_data = await create_room(auth_headers1, session)
        room_code = room_data["room_code"]

        # Test: Update all settings
        new_settings = {
            "problem_count": 7,
            "starting_hp": 300,
            "base_hp_deduction": 4,
            "hp_multiplier_easy": 2.0,
            "hp_multiplier_medium": 2.5,
            "hp_multiplier_hard": 3.0,
            "distribution_mode": "fixed",
            "prob_easy": 0.5,
            "prob_medium": 0.3,
            "prob_hard": 0.2,
            "starting_sp": 200,
            "starting_mp": 200,
            "mana_recharge": 50,
        }
        update_result = await update_room_settings(
            room_code, auth_headers1, session, new_settings
        )

        assert (
            "message" in update_result
            and update_result["message"] == "Settings updated successfully"
        )

        room_info = await get_room(room_code, auth_headers1)
        assert room_info["settings"] == new_settings

        # Test: Update as non-host
        update_result = await update_room_settings(
            room_code, auth_headers2, session, new_settings
        )
        assert (
            "detail" in update_result
            and update_result["detail"] == "Only the host can update room settings"
        )

        await leave_room(room_code, auth_headers1)

        # Test: Update non-existent room
        update_result = await update_room_settings(
            "INVALID", auth_headers1, session, new_settings
        )
        assert "detail" in update_result and update_result["detail"] == "Room not found"

    asyncio.run(test3())
    print("✅")

# Test 4: Lobby WebSocket Tests
if 4 not in SKIP:
    print("Running test 4: Lobby WebSocket Tests", end=" ", flush=True)

    async def test4():
        auth_headers1 = await make_user(
            "rtest6", "rtest6@email.com", "password", "RTester 6"
        )
        auth_headers2 = await make_user(
            "rtest7", "rtest7@email.com", "password", "RTester 7"
        )
        session = requests.Session()

        lobby_url = f"{WS_BASE_URL}/rooms/lobby"

        # Test: Connect to lobby
        async with websockets.connect(
            lobby_url, subprotocols=[f"access_token|{extract_token(auth_headers1)}"]
        ) as lobby_ws:
            # Initial empty room list
            message = await get_latest_message(lobby_ws)
            assert message["type"] == "room_list"
            assert len(message["rooms"]) == 0

            # Create room and check broadcast
            room_data = await create_room(auth_headers2, session)
            message = await get_latest_message(lobby_ws)
            assert message["type"] == "room_list"
            assert len(message["rooms"]) == 1

            # Update settings and check broadcast
            new_settings = {
                "problem_count": 5,
                "starting_hp": 250,
                "base_hp_deduction": 4,
                "hp_multiplier_easy": 1.5,
                "hp_multiplier_medium": 2.0,
                "hp_multiplier_hard": 2.5,
                "distribution_mode": "fixed",
                "prob_easy": 0.4,
                "prob_medium": 0.3,
                "prob_hard": 0.3,
                "starting_sp": 200,
                "starting_mp": 200,
                "mana_recharge": 50,
            }
            await update_room_settings(
                room_data["room_code"], auth_headers2, session, new_settings
            )
            message = await get_latest_message(lobby_ws)
            assert message["type"] == "room_list", "Wrong message type"
            assert message["rooms"][0]["settings"]["problem_count"] == 5

            # Player joins and check broadcast
            async with websockets.connect(
                f"{WS_BASE_URL}/rooms/{room_data['room_code']}",
                subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
            ) as _:
                message = await get_latest_message(lobby_ws)
                assert message["type"] == "room_list"
                assert message["rooms"][0]["player_count"] == 2

            # Player leaves and check broadcast
            message = await get_latest_message(lobby_ws)
            assert message["type"] == "room_list"
            assert message["rooms"][0]["player_count"] == 1

            # Host leaves and check broadcast
            await leave_room(room_data["room_code"], auth_headers2)
            message = await get_latest_message(lobby_ws)
            assert message["type"] == "room_list"
            assert len(message["rooms"]) == 0

    asyncio.run(test4())
    print("✅")

# Test 5: Room WebSocket Basic Tests
if 5 not in SKIP:
    print("Running test 5: Room WebSocket Basic Tests", end=" ", flush=True)

    async def test5():
        auth_headers1 = await make_user(
            "rtest8", "rtest8@email.com", "password", "RTester 8"
        )
        auth_headers2 = await make_user(
            "rtest9", "rtest9@email.com", "password", "RTester 9"
        )
        auth_headers3 = await make_user(
            "rtest10", "rtest10@email.com", "password", "RTester 10"
        )
        session = requests.Session()

        # Test: Connect to non-existent room
        try:
            async with websockets.connect(
                f"{WS_BASE_URL}/rooms/INVALID",
                subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
            ) as ws:
                await ws.recv()
            assert False
        except ConnectionClosedError as e:
            assert e.code == 4004 and e.reason == "Room not found"

        # Create a room and fill it
        room_data = await create_room(auth_headers1, session)
        room_code = room_data["room_code"]

        # Connect host and guest
        async with websockets.connect(
            f"{WS_BASE_URL}/rooms/{room_code}",
            subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
        ) as host_ws:
            async with websockets.connect(
                f"{WS_BASE_URL}/rooms/{room_code}",
                subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
            ) as guest_ws:
                # Test: Verify initial room state messages
                host_state = await get_latest_message(host_ws)
                guest_state = await get_latest_message(guest_ws)

                assert host_state["type"] == "room_state"
                assert guest_state["type"] == "room_state"
                assert not host_state["data"]["host_ready"]
                assert not guest_state["data"]["guest_ready"]

                # Test: Connect to full room
                try:
                    async with websockets.connect(
                        f"{WS_BASE_URL}/rooms/{room_code}",
                        subprotocols=[f"access_token|{extract_token(auth_headers3)}"],
                    ) as third_ws:
                        await asyncio.wait_for(third_ws.recv(), timeout=1)
                except asyncio.TimeoutError:
                    assert False
                except ConnectionClosedError as e:
                    assert e.code == 4003 and e.reason == "Room is full"

        await leave_room(room_code, auth_headers1)
        await leave_room(room_code, auth_headers2)

    asyncio.run(test5())
    print("✅")

# Test 6: Room Ready State and Game Start Tests
if 6 not in SKIP:
    print("Running test 6: Room Ready State and Game Start Tests", end=" ", flush=True)

    async def test6():
        auth_headers1 = await make_user(
            "rtest11", "rtest11@email.com", "password", "RTester 11"
        )
        auth_headers2 = await make_user(
            "rtest12", "rtest12@email.com", "password", "RTester 12"
        )
        session = requests.Session()

        # Create room with custom settings
        room_data = await create_room(auth_headers1, session)
        room_code = room_data["room_code"]

        async with websockets.connect(
            f"{WS_BASE_URL}/rooms/{room_code}",
            subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
        ) as host_ws:
            async with websockets.connect(
                f"{WS_BASE_URL}/rooms/{room_code}",
                subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
            ) as guest_ws:
                # Clear initial messages
                await get_latest_message(host_ws)
                await get_latest_message(guest_ws)

                # Test: Toggle ready states
                await host_ws.send(json.dumps({"type": "toggle_ready"}))
                host_state = await get_latest_message(host_ws)
                await get_latest_message(guest_ws)
                assert host_state["data"]["host_ready"]
                assert not host_state["data"]["guest_ready"]

                await guest_ws.send(json.dumps({"type": "toggle_ready"}))
                host_state = await get_latest_message(host_ws)
                await get_latest_message(guest_ws)
                assert (
                    host_state["data"]["host_ready"]
                    and host_state["data"]["guest_ready"]
                )

                # Test: Start game without being host
                await guest_ws.send(json.dumps({"type": "start_game"}))
                error_msg = await get_latest_message(guest_ws)
                assert error_msg["type"] == "error"
                assert (
                    "Only the host can start the game" in error_msg["data"]["message"]
                )

                # Test: Start game as host
                await host_ws.send(json.dumps({"type": "start_game"}))
                host_game = await get_latest_message(host_ws)
                guest_game = await get_latest_message(guest_ws)
                assert host_game["type"] == "game_started"
                assert "game_id" in host_game["data"]
                game_id = host_game["data"]["game_id"]
                assert game_id == guest_game["data"]["game_id"]

                # Test: Game status is ingame
                room_info = await get_room(room_code, auth_headers1)
                assert room_info["status"] == "in_game"

                # Test: Create room while in game
                room_data2 = await create_room(auth_headers1, session)
                assert (
                    "detail" in room_data2
                    and room_data2["detail"] == "Already in a room"
                )

                # Both players connect to game
                async with websockets.connect(
                    f"{WS_BASE_URL}/game/play/{game_id}",
                    subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
                ) as p1:
                    async with websockets.connect(
                        f"{WS_BASE_URL}/game/play/{game_id}",
                        subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                    ):
                        await send_forfeit(p1)

    asyncio.run(test6())
    print("✅")

# Test 7: Room Chat and Game Integration Tests
if 7 not in SKIP:
    print("Running test 7: Room Chat and Game Integration Tests", end=" ", flush=True)

    async def test7():
        auth_headers1 = await make_user(
            "rtest13", "rtest13@email.com", "password", "RTester 13"
        )
        auth_headers2 = await make_user(
            "rtest14", "rtest14@email.com", "password", "RTester 14"
        )
        session = requests.Session()

        settings = {
            "problem_count": 5,
            "starting_hp": 500,
            "base_hp_deduction": 5,
            "hp_multiplier_easy": 1.0,
            "hp_multiplier_medium": 2.0,
            "hp_multiplier_hard": 3.0,
            "distribution_mode": "fixed",
            "prob_easy": 0.6,
            "prob_medium": 0.2,
            "prob_hard": 0.2,
            "starting_sp": 200,
            "starting_mp": 200,
            "mana_recharge": 50,
        }

        room_data = await create_room(auth_headers1, session, settings=settings)
        room_code = room_data["room_code"]

        async with websockets.connect(
            f"{WS_BASE_URL}/rooms/{room_code}",
            subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
        ) as host_ws:
            async with websockets.connect(
                f"{WS_BASE_URL}/rooms/{room_code}",
                subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
            ) as guest_ws:
                # Clear initial messages
                await get_latest_message(host_ws)
                await get_latest_message(guest_ws)

                # Test: Chat functionality
                chat_message = "Hello, this is a test message!"
                await host_ws.send(
                    json.dumps({"type": "chat", "data": {"message": chat_message}})
                )

                host_chat = await get_latest_message(host_ws)
                guest_chat = await get_latest_message(guest_ws)
                assert host_chat["type"] == "chat"
                assert host_chat["data"]["message"] == chat_message
                assert host_chat["data"]["sender"] == "rtest13"
                assert "timestamp" in host_chat["data"]
                assert guest_chat["data"] == host_chat["data"]

                # Ready up and start game
                await host_ws.send(json.dumps({"type": "toggle_ready"}))
                await guest_ws.send(json.dumps({"type": "toggle_ready"}))
                await get_latest_message(host_ws)
                await get_latest_message(guest_ws)

                await host_ws.send(json.dumps({"type": "start_game"}))
                game_start_host = await get_latest_message(host_ws)
                await get_latest_message(guest_ws)
                game_id = game_start_host["data"]["game_id"]

                # Connect to game and verify settings
                async with websockets.connect(
                    f"{WS_BASE_URL}/game/play/{game_id}",
                    subprotocols=[f"access_token|{extract_token(auth_headers1)}"],
                ) as p1:
                    async with websockets.connect(
                        f"{WS_BASE_URL}/game/play/{game_id}",
                        subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                    ):
                        game_state = await get_until(p1, "game_state")

                        # Test if started game has correct settings
                        assert game_state["data"]["match_type"] == "custom"
                        assert game_state["data"]["your_hp"] == 500
                        assert game_state["data"]["opponent_hp"] == 500
                        assert game_state["data"]["skill_points"] == 200
                        assert game_state["data"]["mana_points"] == 200

                        # Chat and clear initial messages
                        await send_chat(p1, "clear")

                        ALL_SOLUTION = "class Solution:\r\n  def test(self, inp: bool) -> bool:\r\n    return not inp"
                        for _ in range(3):
                            await get_latest_message(p1)
                            await send_code(p1, ALL_SOLUTION)
                            await asyncio.sleep(3)

                        game_state = await get_until(p1, "game_state")
                        assert game_state["data"]["problems_solved"] == 3
                        # First 3 probs are easy, so HP should be 500 - 5 * 10 * 1 * 3 = 350
                        assert game_state["data"]["opponent_hp"] == 350

                        await send_code(p1, ALL_SOLUTION)
                        await asyncio.sleep(3)
                        game_state = await get_until(p1, "game_state")
                        assert game_state["data"]["problems_solved"] == 4
                        # Next prob is medium, so HP should be 350 - 5 * 10 * 2 = 250
                        assert game_state["data"]["opponent_hp"] == 250

                        # Buy and use a healing skill 3 times
                        # Heal 20 * 3 = 60 HP
                        # SP cost is 10
                        # MP cost is 5 * 3 = 15
                        await buy_ability(p1, "healio")
                        await use_ability(p1, "healio")
                        await use_ability(p1, "healio")
                        await get_latest_message(p1)
                        await use_ability(p1, "healio")

                        game_state = await get_until(p1, "game_state")
                        assert game_state["data"]["your_hp"] == 560
                        assert game_state["data"]["skill_points"] == 190
                        assert game_state["data"]["mana_points"] == 200 - 15 + 50 * 4

                        # Buy and use another skill
                        # SP cost is 10
                        # MP cost is 5
                        await buy_ability(p1, "deletio")
                        await get_latest_message(p1)
                        await use_ability(p1, "deletio")

                        game_state = await get_latest_message(p1)
                        assert (
                            game_state["data"]["your_hp"] == 560
                        )  # HP should stay the same
                        assert game_state["data"]["skill_points"] == 180
                        assert (
                            game_state["data"]["mana_points"] == 200 - 15 + 50 * 4 - 5
                        )

                        await send_code(p1, ALL_SOLUTION)
                        await asyncio.sleep(3)
                        game_state = await get_until(p1, "game_state")
                        assert game_state["data"]["problems_solved"] == 5
                        # Last prob is hard, so HP should be 250 - 5 * 10 * 3 = 100
                        assert game_state["data"]["opponent_hp"] == 100

                        # Since all problems are solved, game should end
                        game_end = await get_until(p1, "match_end")
                        assert game_end["data"]["winner"] == "rtest13"

                # Verify room returned to waiting state
                host_state = await get_latest_message(host_ws)
                await get_latest_message(guest_ws)
                assert host_state["data"]["status"] == "waiting"
                assert not host_state["data"]["host_ready"]
                assert not host_state["data"]["guest_ready"]

    asyncio.run(test7())
    print("✅")
