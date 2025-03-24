from api.endpoints.game.controller import router as http_router
from api.endpoints.game.websockets import router as ws_router

__all__ = ["http_router", "ws_router"]
