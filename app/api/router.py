

from fastapi import FastAPI
from api.endpoints import users, game
from core.config import settings


def include_routers(app: FastAPI):
    # add prefix
    app.include_router(users.router, prefix=settings.API_STR)
    app.include_router(game.router, prefix=settings.API_STR)
