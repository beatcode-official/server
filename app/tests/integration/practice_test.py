import os
import subprocess
import sys

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
    print("Running test 1: /practice connection")

    async def test1():
        await make_user("test1", "test1@email.com", "password", "Test User 1")
        access_token = login_user("test1", "password")["access_token"]

        queue_url = f"{WS_BASE_URL}{API_MAP['practice']}"

        # Join queue with valid access token
        try:
            async with websockets.connect(
                queue_url,
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
                queue_url,
                subprotocols=["access_token|random_token_that_shouldnt_fit"],
            ) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except ConnectionClosedError as e:
            assert e.code == 4001
        except Exception:
            assert False

        # Join queue with no access token
        try:
            async with websockets.connect(queue_url) as ws:
                await asyncio.wait_for(ws.recv(), timeout=1)
        except InvalidStatusCode as e:  # 403
            assert e.status_code == 403
        except Exception:
            assert False

    asyncio.run(test1())
    print("✅")
