import asyncio
import json
from pprint import pprint
from typing import Dict

import requests
from tests.integration.constants import *
from tests.integration.constants import VERBOSE
import websockets
from websockets.exceptions import ConnectionClosedError


def register_user(username, email, password, display_name):
    url = f"{BASE_URL}{API_MAP['register']}"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name,
    }

    response = requests.post(url, json=data)
    return response.json()


def login_user(username, password):
    url = f"{BASE_URL}{API_MAP['login']}"
    data = {"username": username, "password": password}

    response = requests.post(url, data=data)
    return response.json()


def verify_email(token):
    url = f"{BASE_URL}{API_MAP['verify']}/{token}"

    response = requests.get(url)
    return response.json()


def get_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(url, headers=headers)
    return response.json()


def update_user(access_token, data):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.patch(url, headers=headers, json=data)
    return response.json()


def delete_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.delete(url, headers=headers)
    return response.json()


def forgot_password(email):
    url = f"{BASE_URL}{API_MAP['forgot']}"
    data = {"email": email}

    response = requests.post(url, json=data)
    return response.json()


def reset_password(token, password):
    url = f"{BASE_URL}{API_MAP['reset']}"
    data = {"token": token, "new_password": password}

    response = requests.post(url, json=data)
    return response.json()


def refresh_token(refresh_token):
    url = f"{BASE_URL}{API_MAP['refresh']}"
    data = {"refresh_token": refresh_token}

    response = requests.post(url, json=data)
    return response.json()


def logout_user(access_token, refresh_token):
    url = f"{BASE_URL}{API_MAP['logout']}"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"refresh_token": refresh_token}

    response = requests.post(url, headers=headers, json=data)
    return response.json()


async def get_current_game(headers):
    url = f"{BASE_URL}{API_MAP['current_game']}"
    response = requests.get(url, headers=headers)
    return response.json()


async def make_user(username, email, password, display_name):
    # Persistent session for faster testing
    session = requests.Session()
    registration_url = f"{BASE_URL}{API_MAP['register']}"
    verify_url = f"{BASE_URL}{API_MAP['verify']}"
    login_url = f"{BASE_URL}{API_MAP['login']}"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name,
    }
    response = session.post(registration_url, json=data)
    session.get(verify_url + "/test_email_token")
    response = session.post(
        login_url, data={"username": username, "password": password}
    )

    response_json = response.json()

    # Handle the typo in the response key (acceess_token instead of access_token)
    if "access_token" in response_json:
        access_token = response_json["access_token"]
    elif "acceess_token" in response_json:
        access_token = response_json["acceess_token"]
    elif "token" in response_json and "access_token" in response_json["token"]:
        access_token = response_json["token"]["access_token"]
    else:
        # Print full response for debugging
        print(f"Full response content: {response.text}")
        raise KeyError(f"Could not find access_token in response: {response_json}")

    return {"Authorization": f"Bearer {access_token}"}


async def get_latest_message(
    ws: websockets.WebSocketClientProtocol, timeout=300
) -> Dict:
    message = None
    while True:
        try:
            message_str = await asyncio.wait_for(ws.recv(), timeout=timeout)
            message = json.loads(message_str)
            if VERBOSE:
                pprint(message)
            return message
        except asyncio.TimeoutError:
            # Will exit loop if no response after timeout
            assert False, f"No response after {timeout}"
        except json.JSONDecodeError:
            assert False, f"Failed to decode JSON: {message}"
        except ConnectionClosedError as e:
            assert False, (
                f"Connection closed while waiting for message: {e.code} {e.reason}"
            )
        except Exception as e:
            assert False, f"Error waiting for/parsing message: {e}"

async def get_until(
    ws: websockets.WebSocketClientProtocol, message_type: str, timeout=300
) -> Dict:
    message = None
    while True:
        try:
            message_str = await asyncio.wait_for(ws.recv(), timeout=timeout)
            message = json.loads(message_str)
            if VERBOSE:
                pprint(message)
            if message.get("type") == message_type:
                break
        except asyncio.TimeoutError:
            assert False, f"No response after {timeout}"
        except json.JSONDecodeError:
            assert False, f"Failed to decode JSON: {message}"
        except ConnectionClosedError as e:
            assert False, (
                f"Connection closed while waiting for message: {e.code} {e.reason}"
            )
        except Exception as e:
            assert False, f"Error waiting for/parsing message: {e}"

    return message


async def send_query(ws: websockets.WebSocketClientProtocol):
    return await ws.send(json.dumps({"type": "query"}))


async def send_forfeit(ws: websockets.WebSocketClientProtocol):
    return await ws.send(json.dumps({"type": "forfeit"}))


async def send_chat(ws: websockets.WebSocketClientProtocol, message: str):
    return await ws.send(json.dumps({"type": "chat", "data": {"message": message}}))


async def send_code(ws: websockets.WebSocketClientProtocol, code: str):
    return await ws.send(
        json.dumps({"type": "submit", "data": {"code": code, "lang": "python"}})
    )


async def buy_ability(ws: websockets.WebSocketClientProtocol, ability_id: str):
    return await ws.send(
        json.dumps(
            {"type": "ability", "data": {"action": "buy", "ability_id": ability_id}}
        )
    )


async def use_ability(ws: websockets.WebSocketClientProtocol, ability_id: str):
    return await ws.send(
        json.dumps(
            {"type": "ability", "data": {"action": "use", "ability_id": ability_id}}
        )
    )


async def create_room(auth_headers, session, settings=None, is_public=None):
    url = f"{BASE_URL}/rooms/create"
    if is_public is not None:
        url += "?is_public=true" if is_public else "?is_public=false"

    if settings is not None:
        response = session.post(url, headers=auth_headers, json=settings)
    else:
        response = session.post(url, headers=auth_headers)

    return response.json()


async def get_room(room_code: str, auth_headers):
    url = f"{BASE_URL}/rooms/{room_code}"
    response = requests.get(url, headers=auth_headers)
    return response.json()


async def update_room_settings(room_code: str, auth_headers, session, settings=None):
    url = f"{BASE_URL}/rooms/{room_code}/settings"
    if settings is not None:
        data = settings
        response = session.patch(url, headers=auth_headers, json=data)
    else:
        response = session.patch(url, headers=auth_headers)

    return response.json()


async def leave_room(room_code: str, auth_headers: dict):
    async with websockets.connect(
        f"{WS_BASE_URL}/rooms/{room_code}",
        subprotocols=[f"access_token|{extract_token(auth_headers)}"],
    ) as ws:
        await ws.close()


def extract_token(auth_header):
    return auth_header["Authorization"].split(" ")[1]


async def wait_for_message(ws, timeout=300):
    """Waits for a message, parses it as JSON, and returns it."""
    message_str = ""
    try:
        message_str = await asyncio.wait_for(ws.recv(), timeout=timeout)
        message = json.loads(message_str)
        if VERBOSE:
            # Use pprint for better readability of complex messages
            pprint(message)
        return message
    except asyncio.TimeoutError:
        assert False, f"No response after {timeout}"
    except json.JSONDecodeError:
        assert False, f"Failed to decode JSON: {message_str}"
    except ConnectionClosedError as e:
        assert False, (
            f"Connection closed while waiting for message: {e.code} {e.reason}"
        )
    except Exception as e:
        assert False, f"Error waiting for/parsing message: {e}"
