import sys

VERBOSE = "-v" in sys.argv
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
    "practice": "/practice",
    "create_room": "/rooms/create",
    "get_room": "/rooms/{room_code}",
    "update_room_settings": "/rooms/{room_code}/settings",
    "lobby": "/rooms/lobby",
    "room_ws": "/rooms/{room_code}",
    "game_ws": "/game/play/{game_id}",
}

UNRANKED_QUEUE_URL = f"{WS_BASE_URL}{API_MAP['queue']}"
RANKED_QUEUE_URL = f"{WS_BASE_URL}{API_MAP['queue_ranked']}"
PRACTICE_URL = f"{WS_BASE_URL}{API_MAP['practice']}"
LOBBY_URL = f"{WS_BASE_URL}{API_MAP['lobby']}"
