# from api.endpoints import game, room, users
import api.endpoints.game as game
import api.endpoints.practice as practice
import api.endpoints.room as room
import api.endpoints.users as users
from core.config import settings
from fastapi import FastAPI


def include_routers(app: FastAPI):
    app.include_router(game.http_router, prefix=settings.API_STR)
    app.include_router(game.ws_router, prefix=settings.API_STR)
    app.include_router(practice.ws_router, prefix=settings.API_STR)
    app.include_router(room.http_router, prefix=settings.API_STR)
    app.include_router(room.ws_router, prefix=settings.API_STR)
    app.include_router(users.http_router, prefix=settings.API_STR)
    app.include_router(users.ws_router, prefix=settings.API_STR)
