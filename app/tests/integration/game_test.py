import json
import os
import subprocess
import sys
import time

from websockets.exceptions import ConnectionClosedError, InvalidStatus

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
    print("Running test 1: /queue and /ranked-queue endpoints", end=" ", flush=True)

    async def test1():
        auth_headers = await make_user(
            "test1", "test1@email.com", "password", "Test User 1"
        )
        test1_access2 = login_user("test1", "password")["access_token"]
        auth_headers_2 = {"Authorization": f"Bearer {test1_access2}"}
        auth_headers2 = await make_user(
            "test2", "test2@email.com", "password", "Test User 2"
        )
        auth_headers3 = await make_user(
            "test3", "test3@email.com", "password", "Test User 3"
        )
        auth_headers4 = await make_user(
            "test4", "test4@email.com", "password", "Test User 4"
        )

        unranked_queue_url = f"{WS_BASE_URL}{API_MAP['queue']}"
        ranked_queue_url = f"{WS_BASE_URL}{API_MAP['queue_ranked']}"

        # Join queue with valid access token
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        # Join queue with invalid access token
        fake_headers = {"Authorization": "Bearer fake_token"}
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(fake_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4001
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(fake_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4001
        except Exception:
            assert False

        # Join queue with no access token
        try:
            async with websockets.connect(unranked_queue_url) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except InvalidStatus:  # 403
            assert True
        except Exception:
            assert False

        try:
            async with websockets.connect(ranked_queue_url) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except InvalidStatus:  # 403
            assert True
        except Exception:
            assert False

        # Join queue when already in queue (same access token)
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        # Join queue when already in queue (different access token)
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        # Join unranked queue when already in ranked queue and vice versa
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False

        # Leave queue and rejoin
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        # Join queue on one connection, leave and join on another
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
            ) as ws:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except TimeoutError:
                    pass

            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers_2)}"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except TimeoutError:
            assert True
        except Exception:
            assert False

        # Join queue when already in a match and then join queue after finishing a match
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    response = await ws1.recv()
                    match_id = json.loads(response)["data"]["match_id"]

                    async with websockets.connect(
                        ranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                    ) as ws:
                        await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False
        finally:
            async with websockets.connect(
                f"{WS_BASE_URL}/game/play/{match_id}",
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as game_ws:
                await game_ws.send(json.dumps({"type": "forfeit"}))

            try:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except TimeoutError:
                assert True
            except Exception:
                assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    response = await ws1.recv()
                    match_id = json.loads(response)["data"]["match_id"]

                    async with websockets.connect(
                        ranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                    ) as ws:
                        await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4000
        except Exception:
            assert False
        finally:
            async with websockets.connect(
                f"{WS_BASE_URL}/game/play/{match_id}",
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as game_ws:
                await game_ws.send(json.dumps({"type": "forfeit"}))

            try:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except TimeoutError:
                assert True
            except Exception:
                assert False

        # Join queue as 2 players and get matched
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    response1 = await ws1.recv()
                    response2 = await ws2.recv()
                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]
                    async with websockets.connect(
                        f"{WS_BASE_URL}/game/play/{match_id}",
                        subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                    ) as game_ws:
                        await game_ws.send(json.dumps({"type": "forfeit"}))
        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    response1 = await ws1.recv()
                    response2 = await ws2.recv()
                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]
                    async with websockets.connect(
                        f"{WS_BASE_URL}/game/play/{match_id}",
                        subprotocols=[f"access_token|{extract_token(auth_headers)}"],
                    ) as game_ws:
                        await game_ws.send(json.dumps({"type": "forfeit"}))
        except Exception:
            assert False

        # Join queue as 3 players and 2 get matched
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    async with websockets.connect(
                        unranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers3)}"],
                    ) as ws3:
                        response1 = None
                        response2 = None
                        response3 = None

                        try:
                            response1 = await asyncio.wait_for(ws1.recv(), timeout=3)
                            response2 = await asyncio.wait_for(ws2.recv(), timeout=3)
                            response3 = await asyncio.wait_for(ws3.recv(), timeout=3)
                        except TimeoutError:
                            pass

                        responses = [response1, response2, response3]
                        valid_indexes = []
                        user_to_match_id = {}
                        for i in range(3):
                            if responses[i]:
                                valid_indexes.append(i)
                                user_to_match_id[
                                    json.loads(responses[i])["data"]["match_id"]
                                ] = i

                        assert len(valid_indexes) == 2
                        assert len(user_to_match_id) == 1

                        auth_headers_list = [auth_headers, auth_headers2, auth_headers3]
                        match_id = list(user_to_match_id.keys())[0]
                        user_index1 = user_to_match_id[match_id]

                        async with websockets.connect(
                            f"{WS_BASE_URL}/game/play/{match_id}",
                            subprotocols=[
                                f"access_token|{extract_token(auth_headers_list[user_index1])}"
                            ],
                        ) as game_ws:
                            await game_ws.send(json.dumps({"type": "forfeit"}))

        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    async with websockets.connect(
                        ranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers3)}"],
                    ) as ws3:
                        response1 = None
                        response2 = None
                        response3 = None

                        try:
                            response1 = await asyncio.wait_for(ws1.recv(), timeout=3)
                            response2 = await asyncio.wait_for(ws2.recv(), timeout=3)
                            response3 = await asyncio.wait_for(ws3.recv(), timeout=3)
                        except TimeoutError:
                            pass

                        responses = [response1, response2, response3]
                        valid_indexes = []
                        user_to_match_id = {}
                        for i in range(3):
                            if responses[i]:
                                valid_indexes.append(i)
                                user_to_match_id[
                                    json.loads(responses[i])["data"]["match_id"]
                                ] = i

                        assert len(valid_indexes) == 2
                        assert len(user_to_match_id) == 1

                        auth_headers_list = [auth_headers, auth_headers2, auth_headers3]
                        match_id = list(user_to_match_id.keys())[0]
                        user_index1 = user_to_match_id[match_id]

                        async with websockets.connect(
                            f"{WS_BASE_URL}/game/play/{match_id}",
                            subprotocols=[
                                f"access_token|{extract_token(auth_headers_list[user_index1])}"
                            ],
                        ) as game_ws:
                            await game_ws.send(json.dumps({"type": "forfeit"}))

        except Exception:
            assert False

        # Join queue as 4 players and all 4 get matched
        try:
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    async with websockets.connect(
                        unranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers3)}"],
                    ) as ws3:
                        async with websockets.connect(
                            unranked_queue_url,
                            subprotocols=[
                                f"access_token|{extract_token(auth_headers4)}"
                            ],
                        ) as ws4:
                            response1 = None
                            response2 = None
                            response3 = None
                            response4 = None

                            try:
                                response1 = await asyncio.wait_for(
                                    ws1.recv(), timeout=5
                                )
                                response2 = await asyncio.wait_for(
                                    ws2.recv(), timeout=5
                                )
                                response3 = await asyncio.wait_for(
                                    ws3.recv(), timeout=5
                                )
                                response4 = await asyncio.wait_for(
                                    ws4.recv(), timeout=5
                                )
                            except TimeoutError:
                                pass

                            responses = [response1, response2, response3, response4]
                            valid_indexes = []
                            user_to_match_id = {}
                            for i in range(4):
                                if responses[i]:
                                    valid_indexes.append(i)
                                    user_to_match_id[
                                        json.loads(responses[i])["data"]["match_id"]
                                    ] = i

                            assert len(valid_indexes) == 4
                            assert len(user_to_match_id) == 2

                            auth_headers_list = [
                                auth_headers,
                                auth_headers2,
                                auth_headers3,
                                auth_headers4,
                            ]
                            match_id_1 = list(user_to_match_id.keys())[0]
                            user_index1 = user_to_match_id[match_id_1]
                            match_id_2 = list(user_to_match_id.keys())[1]
                            user_index2 = user_to_match_id[match_id_2]

                            async with websockets.connect(
                                f"{WS_BASE_URL}/game/play/{match_id_1}",
                                subprotocols=[
                                    f"access_token|{extract_token(auth_headers_list[user_index1])}"
                                ],
                            ) as game_ws:
                                await game_ws.send(json.dumps({"type": "forfeit"}))

                            async with websockets.connect(
                                f"{WS_BASE_URL}/game/play/{match_id_2}",
                                subprotocols=[
                                    f"access_token|{extract_token(auth_headers_list[user_index2])}"
                                ],
                            ) as game_ws:
                                await game_ws.send(json.dumps({"type": "forfeit"}))

        except Exception:
            assert False

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(auth_headers)}"],
            ) as ws1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(auth_headers2)}"],
                ) as ws2:
                    async with websockets.connect(
                        ranked_queue_url,
                        subprotocols=[f"access_token|{extract_token(auth_headers3)}"],
                    ) as ws3:
                        async with websockets.connect(
                            ranked_queue_url,
                            subprotocols=[
                                f"access_token|{extract_token(auth_headers4)}"
                            ],
                        ) as ws4:
                            response1 = None
                            response2 = None
                            response3 = None
                            response4 = None

                            try:
                                response1 = await asyncio.wait_for(
                                    ws1.recv(), timeout=5
                                )
                                response2 = await asyncio.wait_for(
                                    ws2.recv(), timeout=5
                                )
                                response3 = await asyncio.wait_for(
                                    ws3.recv(), timeout=5
                                )
                                response4 = await asyncio.wait_for(
                                    ws4.recv(), timeout=5
                                )
                            except TimeoutError:
                                pass

                            responses = [response1, response2, response3, response4]
                            valid_indexes = []
                            user_to_match_id = {}
                            for i in range(4):
                                if responses[i]:
                                    valid_indexes.append(i)
                                    user_to_match_id[
                                        json.loads(responses[i])["data"]["match_id"]
                                    ] = i

                            assert len(valid_indexes) == 4
                            assert len(user_to_match_id) == 2

                            auth_headers_list = [
                                auth_headers,
                                auth_headers2,
                                auth_headers3,
                                auth_headers4,
                            ]
                            match_id_1 = list(user_to_match_id.keys())[0]
                            user_index1 = user_to_match_id[match_id_1]
                            match_id_2 = list(user_to_match_id.keys())[1]
                            user_index2 = user_to_match_id[match_id_2]

                            async with websockets.connect(
                                f"{WS_BASE_URL}/game/play/{match_id_1}",
                                subprotocols=[
                                    f"access_token|{extract_token(auth_headers_list[user_index1])}"
                                ],
                            ) as game_ws:
                                await game_ws.send(json.dumps({"type": "forfeit"}))

                            async with websockets.connect(
                                f"{WS_BASE_URL}/game/play/{match_id_2}",
                                subprotocols=[
                                    f"access_token|{extract_token(auth_headers_list[user_index2])}"
                                ],
                            ) as game_ws:
                                await game_ws.send(json.dumps({"type": "forfeit"}))

        except Exception:
            assert False

    asyncio.run(test1())

    print("✅")

# Test 2
if 2 not in SKIP:
    print("Running test 2: /game endpoint", end=" ", flush=True)

    async def test2():
        p1_auth_headers = await make_user(
            "player1", "player1@email.com", "password", "Player 1"
        )
        p2_auth_headers = await make_user(
            "player2", "player2@email.com", "password", "Player 2"
        )
        p3_auth_headers = await make_user(
            "player3", "player3@email.com", "password", "Player 3"
        )
        # p4_auth_headers = await make_user(
        #     "player4", "player4@email.com", "password", "Player 4"
        # )

        unranked_queue_url = f"{WS_BASE_URL}{API_MAP['queue']}"
        ranked_queue_url = f"{WS_BASE_URL}{API_MAP['queue_ranked']}"
        game_url = f"{WS_BASE_URL}/game/play/"

        ERROR_SOLUTION = "class Solution:\r\n  def NOTTEST(self, inp: bool) -> bool:\r\n    return not inp"
        NONE_SOLUTION = (
            "class Solution:\r\n  def test(self, inp: bool) -> bool:\r\n    return inp"
        )
        SOME_SOLUTION1 = "class Solution:\r\n  def test(self, inp: bool) -> bool:\r\n    return False"
        SOME_SOLUTION2 = (
            "class Solution:\r\n  def test(self, inp: bool) -> bool:\r\n    return True"
        )
        ALL_SOLUTION = "class Solution:\r\n  def test(self, inp: bool) -> bool:\r\n    return not inp"

        try:
            # Join queue as 2 players and get matched
            async with websockets.connect(
                unranked_queue_url,
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as q1:
                async with websockets.connect(
                    unranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as q2:
                    response1 = await q1.recv()
                    response2 = await q2.recv()

                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]

            # Join with no access token
            try:
                async with websockets.connect(f"{game_url}{match_id}") as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except InvalidStatus:  # 403
                assert True
            except Exception:
                assert False

            # Join with invalid access token
            fake_headers = {"Authorization": "Bearer fake"}
            try:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(fake_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except ConnectionClosedError as e:
                assert e.code == 4001
            except Exception:
                assert False

            # Join non-existent game
            try:
                async with websockets.connect(
                    f"{game_url}fake",
                    subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except ConnectionClosedError as e:
                assert e.code == 4000
            except Exception:
                assert False

            # Join as a non-player
            try:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p3_auth_headers)}"],
                ) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=1)
            except ConnectionClosedError as e:
                assert e.code == 4000
            except Exception:
                assert False

            # Join while in another connection
            try:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
                ) as ws1:
                    async with websockets.connect(
                        f"{game_url}{match_id}",
                        subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
                    ) as ws2:
                        await asyncio.wait_for(ws1.recv(), timeout=5)
                        await asyncio.wait_for(ws2.recv(), timeout=5)
            except ConnectionClosedError:
                assert True
            except Exception:
                assert False

            # Game state is waiting every rejoin and doesn't start until 2 players join
            try:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
                ) as p1:
                    response = await asyncio.wait_for(p1.recv(), timeout=5)
                    assert json.loads(response)["data"]["status"] == "waiting"

                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
                ) as p1:
                    p1_response = await asyncio.wait_for(p1.recv(), timeout=5)
                    assert json.loads(p1_response)["data"]["status"] == "waiting"

                    async with websockets.connect(
                        f"{game_url}{match_id}",
                        subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                    ) as p2:
                        p1_response = await asyncio.wait_for(p1.recv(), timeout=5)
                        assert json.loads(p1_response)["type"] == "game_start"

                        await asyncio.wait_for(p2.recv(), timeout=5)
                        p2_response = await asyncio.wait_for(p2.recv(), timeout=5)

                        assert json.loads(p2_response)["type"] == "game_start"

            except Exception:
                assert False

            async with websockets.connect(
                f"{game_url}{match_id}",
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as p1:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as p2:
                    await get_latest_message(p1)
                    await get_latest_message(p2)

            async with websockets.connect(
                f"{game_url}{match_id}",
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as p1:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as p2:
                    # Game state is in-progress every rejoin
                    p1_resp = await asyncio.wait_for(p1.recv(), timeout=5)
                    assert json.loads(p1_resp)["data"]["status"] == "in_progress"

                    # Check if current problem is received every rejoin
                    p1_resp = await asyncio.wait_for(p1.recv(), timeout=5)
                    assert json.loads(p1_resp)["type"] == "problem"

                    # Chat received two sides, correct timestamps
                    curtime = round(time.time())
                    await send_chat(p1, "Test")

                    p1_resp = await get_latest_message(p1)
                    assert p1_resp["type"] == "chat"
                    assert p1_resp["data"]["message"] == "Test"
                    assert (
                        curtime - 2
                        <= round(p1_resp["data"]["timestamp"])
                        <= curtime + 2
                    )
                    assert p1_resp["data"]["sender"] == "player1"

                    p2_resp = await get_latest_message(p2)
                    assert p2_resp["type"] == "chat"
                    assert p2_resp["data"]["message"] == "Test"
                    assert (
                        curtime - 2
                        <= round(p2_resp["data"]["timestamp"])
                        <= curtime + 2
                    )
                    assert p2_resp["data"]["sender"] == "player1"

                    # Query to get game state
                    await send_query(p1)
                    p1_resp = await get_latest_message(p1)
                    assert p1_resp["type"] == "game_state"
                    assert p1_resp["data"]["status"] == "in_progress"

                    await get_latest_message(p1)
                    await get_latest_message(p2)

                    # Solution causes error
                    await send_code(p1, ERROR_SOLUTION)

                    p1_resp = await get_until(p1, "submission_result")

                    assert p1_resp["data"]["summary"]["passed_tests"] == 0
                    assert p1_resp["data"]["test_results"][0]["error"]

                    # Submit too quickly
                    await send_code(p1, ERROR_SOLUTION)

                    p1_resp = await get_until(p1, "error")
                    assert "submitting too fast" in p1_resp["data"]["message"]

                    # Solution solved none
                    await asyncio.sleep(3)
                    await send_code(p1, NONE_SOLUTION)

                    p1_resp = await get_until(p1, "submission_result")
                    assert p1_resp["data"]["summary"]["passed_tests"] == 0
                    p1_resp = await get_until(p1, "game_state")
                    assert p1_resp["data"]["opponent_hp"] == 140

                    # Solution solved some
                    await asyncio.sleep(3)
                    await send_code(p1, SOME_SOLUTION1)

                    p1_resp = await get_until(p1, "submission_result")
                    assert p1_resp["data"]["summary"]["passed_tests"] == 7
                    p1_resp = await get_until(p1, "game_state")
                    assert p1_resp["data"]["opponent_hp"] == 112

                    await asyncio.sleep(3)
                    await send_code(p1, SOME_SOLUTION2)

                    p1_resp = await get_until(p1, "submission_result")
                    assert p1_resp["data"]["summary"]["passed_tests"] == 3
                    p1_resp = await get_until(p1, "game_state")
                    assert p1_resp["data"]["opponent_hp"] == 112

                    # Solution solved all
                    await asyncio.sleep(3)
                    await send_code(p1, ALL_SOLUTION)

                    p1_resp = await get_until(p1, "submission_result")
                    assert p1_resp["data"]["summary"]["passed_tests"] == 10
                    p1_resp = await get_until(p1, "game_state")
                    assert p1_resp["data"]["opponent_hp"] == 100
                    assert p1_resp["data"]["problems_solved"] == 1

                    # Solved all = win
                    await asyncio.sleep(3)
                    await send_code(p1, ALL_SOLUTION)

                    await asyncio.sleep(3)
                    await send_code(p1, ALL_SOLUTION)

                    p1_resp = await get_latest_message(p1)
                    assert p1_resp["type"] == "match_end"
                    assert p1_resp["data"]["winner"] == "player1"
                    assert p1_resp["data"]["problems_solved"] == 3
                    assert p1_resp["data"]["opponent_hp"] == 20
                    assert p1_resp["data"]["status"] == "finished"

                    p2_resp = await get_latest_message(p2)
                    assert p2_resp["type"] == "match_end"
                    assert p2_resp["data"]["winner"] == "player1"
                    assert p2_resp["data"]["problems_solved"] == 0
                    assert p2_resp["data"]["opponent_hp"] == 140
                    assert p2_resp["data"]["status"] == "finished"

                    # Chat events and submissions aren't processed after game finished
                    await send_chat(p1, "Test")
                    await send_code(p1, ALL_SOLUTION)

                    p1_resp = await get_latest_message(p1)
                    p2_resp = await get_latest_message(p2)

                    assert p1_resp is None
                    assert p2_resp is None

        except Exception:
            assert False

        # Opponent HP = 0 = win
        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as q1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as q2:
                    response1 = await q1.recv()
                    response2 = await q2.recv()

                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]

            async with websockets.connect(
                f"{game_url}{match_id}",
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as p1:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as p2:
                    await send_code(p1, ALL_SOLUTION)
                    await asyncio.sleep(3)
                    await send_code(p1, ALL_SOLUTION)

                    p1_resp = await get_latest_message(p1)
                    assert p1_resp["type"] == "match_end"
                    assert p1_resp["data"]["winner"] == "player1"
                    assert p1_resp["data"]["problems_solved"] == 2
                    assert p1_resp["data"]["opponent_hp"] == 0
                    assert p1_resp["data"]["status"] == "finished"

                    p2_resp = await get_latest_message(p2)
                    assert p2_resp["type"] == "match_end"
                    assert p2_resp["data"]["winner"] == "player1"
                    assert p2_resp["data"]["problems_solved"] == 0
                    assert p2_resp["data"]["opponent_hp"] == 140
                    assert p2_resp["data"]["status"] == "finished"

        except Exception:
            assert False

        # Forfeit end game immediately, winner correctly decided (solely based on who surrendered)
        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as q1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as q2:
                    response1 = await q1.recv()
                    response2 = await q2.recv()

                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]

            async with websockets.connect(
                f"{game_url}{match_id}",
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as p1:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as p2:
                    await send_code(p1, ALL_SOLUTION)
                    await send_forfeit(p1)

                    p1_resp = await get_latest_message(p1)
                    assert p1_resp["type"] == "match_end"
                    assert p1_resp["data"]["winner"] == "player2"
                    assert p1_resp["data"]["problems_solved"] == 1
                    assert p1_resp["data"]["opponent_hp"] == 60
                    assert p1_resp["data"]["status"] == "finished"

                    p2_resp = await get_latest_message(p2)
                    assert p2_resp["type"] == "match_end"
                    assert p2_resp["data"]["winner"] == "player2"
                    assert p2_resp["data"]["problems_solved"] == 0
                    assert p2_resp["data"]["opponent_hp"] == 140
                    assert p2_resp["data"]["status"] == "finished"

        except Exception:
            assert False

        # # Timeout, winner correctly decided (based on hp)
        # # Change services.game.state.GameState.is_timed_out to 20 second for this test
        # try:
        #     async with websockets.connect(
        #         ranked_queue_url,
        #         subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"]
        #     ) as q1:
        #         async with websockets.connect(
        #             ranked_queue_url,
        #             subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"]
        #         ) as q2:
        #             response1 = await q1.recv()
        #             response2 = await q2.recv()

        #             assert json.loads(response1)["data"]["match_id"] == json.loads(response2)["data"]["match_id"]

        #             match_id_1 = json.loads(response1)["data"]["match_id"]

        #             async with websockets.connect(
        #                 ranked_queue_url,
        #                 subprotocols=[f"access_token|{extract_token(p3_auth_headers)}"]
        #             ) as q3:
        #                 async with websockets.connect(
        #                     ranked_queue_url,
        #                     subprotocols=[f"access_token|{extract_token(p4_auth_headers)}"]
        #                 ) as q4:
        #                     response3 = await q3.recv()
        #                     response4 = await q4.recv()

        #                     assert json.loads(response3)["data"]["match_id"] == json.loads(response4)["data"]["match_id"]

        #                     match_id_2 = json.loads(response3)["data"]["match_id"]

        #     async with websockets.connect(
        #         f"{game_url}{match_id_1}",
        #         subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"]
        #     ) as p1:
        #         async with websockets.connect(
        #             f"{game_url}{match_id_1}",
        #             subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"]
        #         ) as p2:
        #             async with websockets.connect(
        #                 f"{game_url}{match_id_2}",
        #                 subprotocols=[f"access_token|{extract_token(p3_auth_headers)}"]
        #             ) as p3:
        #                 async with websockets.connect(
        #                     f"{game_url}{match_id_2}",
        #                     subprotocols=[f"access_token|{extract_token(p4_auth_headers)}"]
        #                 ) as p4:
        #                     # First pair, send code until hp is 4 vs 36
        #                     await send_code(p1, ALL_SOLUTION)
        #                     await send_code(p2, ALL_SOLUTION)
        #                     await asyncio.sleep(3)
        #                     await send_code(p1, SOME_SOLUTION2)  # 3/10
        #                     await send_code(p2, SOME_SOLUTION1)  # 7/10

        #                     # Second pair, do nothing so it results in a draw
        #                     await asyncio.sleep(20)

        #                     # Check results
        #                     p1_resp = await get_latest_message(p1)
        #                     assert p1_resp["type"] == "match_end"
        #                     assert p1_resp["data"]["winner"] == "player2"
        #                     assert p1_resp["data"]["problems_solved"] == 1
        #                     assert p1_resp["data"]["opponent_hp"] == 36
        #                     assert p1_resp["data"]["status"] == "finished"

        #                     p2_resp = await get_latest_message(p2)
        #                     assert p2_resp["type"] == "match_end"
        #                     assert p2_resp["data"]["winner"] == "player2"
        #                     assert p2_resp["data"]["problems_solved"] == 1
        #                     assert p2_resp["data"]["opponent_hp"] == 4
        #                     assert p2_resp["data"]["status"] == "finished"

        #                     p3_resp = await get_latest_message(p3)
        #                     assert p3_resp["type"] == "match_end"
        #                     assert p3_resp["data"]["winner"] is None
        #                     assert p3_resp["data"]["problems_solved"] == 0
        #                     assert p3_resp["data"]["opponent_hp"] == 140
        #                     assert p3_resp["data"]["status"] == "finished"

        #                     p4_resp = await get_latest_message(p4)
        #                     assert p4_resp["type"] == "match_end"
        #                     assert p4_resp["data"]["winner"] is None
        #                     assert p4_resp["data"]["problems_solved"] == 0
        #                     assert p4_resp["data"]["opponent_hp"] == 140
        #                     assert p4_resp["data"]["status"] == "finished"

        # except Exception:
        #     assert False

    asyncio.run(test2())

    print("✅")


if 3 not in SKIP:
    # Test 3
    print("Running test 3: /current-game endpoint", end=" ", flush=True)

    async def test3():
        p1_auth_headers = await make_user(
            "skibidi1", "skibidi1@email.com", "password", "Skibidi 1"
        )
        p2_auth_headers = await make_user(
            "skibidi2", "skibidi2@email.com", "password", "Skibidi 2"
        )

        ranked_queue_url = f"{WS_BASE_URL}{API_MAP['queue_ranked']}"
        game_url = f"{WS_BASE_URL}/game/play/"

        # No current game
        cur_game = await get_current_game(p1_auth_headers)
        assert cur_game is None

        try:
            async with websockets.connect(
                ranked_queue_url,
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as q1:
                async with websockets.connect(
                    ranked_queue_url,
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ) as q2:
                    response1 = await q1.recv()
                    response2 = await q2.recv()

                    assert (
                        json.loads(response1)["data"]["match_id"]
                        == json.loads(response2)["data"]["match_id"]
                    )

                    match_id = json.loads(response1)["data"]["match_id"]

            cur_game1 = await get_current_game(p1_auth_headers)
            cur_game2 = await get_current_game(p2_auth_headers)
            assert cur_game1["match_id"] == match_id
            assert cur_game2["match_id"] == match_id
            assert cur_game1["status"] == "waiting"
            assert cur_game2["status"] == "waiting"

            async with websockets.connect(
                f"{game_url}{match_id}",
                subprotocols=[f"access_token|{extract_token(p1_auth_headers)}"],
            ) as p1:
                async with websockets.connect(
                    f"{game_url}{match_id}",
                    subprotocols=[f"access_token|{extract_token(p2_auth_headers)}"],
                ):
                    cur_game1 = await get_current_game(p1_auth_headers)
                    cur_game2 = await get_current_game(p2_auth_headers)

                    assert cur_game1["status"] == "in_progress"
                    assert cur_game2["status"] == "in_progress"

                    await send_forfeit(p1)

                    cur_game1 = await get_current_game(p1_auth_headers)
                    cur_game2 = await get_current_game(p2_auth_headers)

                    assert cur_game1 is None
                    assert cur_game2 is None

        except Exception:
            assert False

    asyncio.run(test3())

    print("✅")
