import asyncio
import json
from pprint import pprint

import requests
import websockets

BASE_URL = "http://localhost:8000/api"
WS_BASE_URL = "ws://localhost:8000/api"
API_MAP = {
    "register": "/users/register",
    "login": "/users/login",
    "verify": "/users/verify-email",
    "user": "/users/me",
    "forgot": "/users/forgot-password",
    "reset": "/users/reset-password",
    "refresh": "/users/refresh",
    "logout": "/users/logout",
    "queue": "/game/queue",
    "queue_ranked": "/game/ranked-queue",
    "current_game": "/game/current-game",
}


def register_user(username, email, password, display_name):
    url = f"{BASE_URL}{API_MAP['register']}"
    data = {
        "username": username,
        "email": email,
        "password": password,
        "display_name": display_name
    }

    response = requests.post(url, json=data)
    return response.json()


def login_user(username, password):
    url = f"{BASE_URL}{API_MAP['login']}"
    data = {
        "username": username,
        "password": password
    }

    response = requests.post(url, data=data)
    return response.json()


def verify_email(token):
    url = f"{BASE_URL}{API_MAP['verify']}/{token}"

    response = requests.get(url)
    return response.json()


def get_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    return response.json()


def update_user(access_token, data):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.patch(url, headers=headers, json=data)
    return response.json()


def delete_user(access_token):
    url = f"{BASE_URL}{API_MAP['user']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.delete(url, headers=headers)


def forgot_password(email):
    url = f"{BASE_URL}{API_MAP['forgot']}"
    data = {
        "email": email
    }

    response = requests.post(url, json=data)
    return response.json()


def reset_password(token, password):
    url = f"{BASE_URL}{API_MAP['reset']}"
    data = {
        "token": token,
        "new_password": password
    }

    response = requests.post(url, json=data)
    return response.json()


def refresh_token(refresh_token):
    url = f"{BASE_URL}{API_MAP['refresh']}"
    data = {
        "refresh_token": refresh_token
    }

    response = requests.post(url, json=data)
    return response.json()


def logout_user(access_token, refresh_token):
    url = f"{BASE_URL}{API_MAP['logout']}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    data = {
        "refresh_token": refresh_token
    }

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
        "display_name": display_name
    }
    response = session.post(registration_url, json=data)
    session.get(verify_url + "/test_email_token")
    response = session.post(login_url, data={"username": username, "password": password})
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


async def get_latest_message(ws: websockets.WebSocketClientProtocol, print_all=False):
    message = None
    while True:
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=1)
            message = json.loads(message)
            if print_all:
                pprint(message)
        except asyncio.TimeoutError:
            break

    return message


async def get_until(ws: websockets.WebSocketClientProtocol, message_type: str):
    message = None
    while True:
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=1)
            message = json.loads(message)
            if message["type"] == message_type:
                break
        except asyncio.TimeoutError:
            break

    return message


async def send_query(ws: websockets.WebSocketClientProtocol):
    return await ws.send(json.dumps({"type": "query"}))


async def send_forfeit(ws: websockets.WebSocketClientProtocol):
    return await ws.send(json.dumps({"type": "forfeit"}))


async def send_chat(ws: websockets.WebSocketClientProtocol, message: str):
    return await ws.send(json.dumps({
        "type": "chat",
        "data": {
            "message": message
        }
    }))


async def send_code(ws: websockets.WebSocketClientProtocol, code: str):
    return await ws.send(json.dumps({
        "type": "submit",
        "data": {
            "code": code
        }
    }))


async def buy_ability(ws: websockets.WebSocketClientProtocol, ability_id: str):
    return await ws.send(json.dumps({
        "type": "ability",
        "data": {
            "action": "buy",
            "ability_id": ability_id
        }
    }))


async def use_ability(ws: websockets.WebSocketClientProtocol, ability_id: str):
    return await ws.send(json.dumps({
        "type": "ability",
        "data": {
            "action": "use",
            "ability_id": ability_id
        }
    }))


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
    async with websockets.connect(f"{WS_BASE_URL}/rooms/{room_code}", subprotocols=[f"access_token|{extract_token(auth_headers)}"]) as ws:
        await ws.close()


def extract_token(auth_header):
    return auth_header['Authorization'].split(" ")[1]
