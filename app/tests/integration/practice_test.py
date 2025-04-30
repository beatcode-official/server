import os
import subprocess
import sys

from websockets.exceptions import ConnectionClosedError, InvalidStatus

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.config import settings
from tests.integration.constants import *
from tests.integration.functions import *

assert settings.TESTING, "Server is not in testing mode"
subprocess.run(["python", "-m", "db.init", "--droptest"], stdout=subprocess.DEVNULL)


SKIP = []
ws_url = f"{WS_BASE_URL}{API_MAP['practice']}"
print(f"Skipping tests: {SKIP}")

# Test 1
if 1 not in SKIP:
    print(
        "Running test 1: Test invalid connections",
        end=("\n" if VERBOSE else " "),
        flush=True,
    )

    async def test1():
        await make_user("test1", "test1@email.com", "password", "Test User")
        access_token = login_user("test1", "password")["access_token"]

        # Join queue with valid access token
        try:
            async with websockets.connect(
                ws_url,
                subprotocols=[f"access_token|{access_token}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        # Join queue with invalid access token
        try:
            async with websockets.connect(
                ws_url,
                subprotocols=["access_token|random_token_that_shouldnt_fit"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4001
        except Exception:
            assert False

        # Join queue with no access token
        try:
            async with websockets.connect(ws_url) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except InvalidStatus:  # 403
            assert True
        except Exception:
            assert False

    asyncio.run(test1())
    print("✅")

if 2 not in SKIP:
    print(
        "Running test 2: Player do nothing", end=("\n" if VERBOSE else " "), flush=True
    )

    async def test2():
        await make_user("test2", "test2@email.com", "password", "Test User")
        access_token = login_user("test2", "password")["access_token"]

        async with websockets.connect(
            ws_url,
            subprotocols=[f"access_token|{access_token}"],
        ) as ws:
            msg = await wait_for_message(ws)
            assert msg.get("type") == "game_state", (
                f"Expected type 'problem', got {msg.get('type', 'None')}"
            )

            msg = await get_until(ws, "problem")
            msg = await get_until(ws, "chat")
            while msg.get("type") == "chat":
                msg = await wait_for_message(ws)

            # change to hard so the bot can act faster
            change_diff = {
                "type": "change_bot_difficulty",
                "data": {"difficulty": "hard"},
            }
            await ws.send(json.dumps(change_diff))
            msg = await get_until(ws, "chat")

            # bot must use ability at some point
            msg = await get_until(ws, "ability_used")

            # bot must deal damage at some point
            msg = await get_until(ws, "game_state")
            assert msg["data"]["your_hp"] < 140, msg

    asyncio.run(test2())
    print("✅")

if 3 not in SKIP:
    print(
        "Running test 3: Player uses ability",
        end=("\n" if VERBOSE else " "),
        flush=True,
    )

    async def test3():
        await make_user("test3", "test3@email.com", "password", "Test User")
        access_token = login_user("test3", "password")["access_token"]

        async with websockets.connect(
            ws_url,
            subprotocols=[f"access_token|{access_token}"],
        ) as ws:
            msg = await wait_for_message(ws)
            assert msg.get("type") == "game_state", (
                f"Expected type 'problem', got {msg.get('type', 'None')}"
            )

            msg = await wait_for_message(ws)
            assert msg.get("type") == "problem", (
                f"Expected type 'problem', got {msg.get('type', 'None')}"
            )

            msg = await get_until(ws, "ability_bought")
            while msg.get("type") == "ability_bought":
                msg = await wait_for_message(ws)
            print(msg)

            msg = await get_until(ws, "chat")
            while msg.get("type") == "chat":
                msg = await wait_for_message(ws)
            print(msg)

            buy_ability = {
                "type": "ability",
                "data": {"action": "buy", "ability_id": "healio"},
            }
            await ws.send(json.dumps(buy_ability))
            msg = await get_until(ws, "ability_bought")
            assert msg is not None

            msg = await get_until(ws, "chat")

            use_ability = {
                "type": "ability",
                "data": {"action": "use", "ability_id": "healio"},
            }
            await ws.send(json.dumps(use_ability))
            await get_until(ws, "ability_used")

    asyncio.run(test3())
    print("✅")
