

from fastapi import FastAPI
from api.endpoints import users, game, room
from core.config import settings


def include_routers(app: FastAPI):
    app.include_router(users.router, prefix=settings.API_STR)
    app.include_router(game.router, prefix=settings.API_STR)
    app.include_router(room.router, prefix=settings.API_STR)
