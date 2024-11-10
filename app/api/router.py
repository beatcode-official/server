from api.endpoints import game, room, users
from core.config import settings
from fastapi import FastAPI


def include_routers(app: FastAPI):
    app.include_router(users.router, prefix=settings.API_STR)
    app.include_router(game.router, prefix=settings.API_STR)
    app.include_router(room.router, prefix=settings.API_STR)
