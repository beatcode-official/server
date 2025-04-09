from api.endpoints.room.controller import router as http_router
from api.endpoints.room.websockets import router as ws_router

__all__ = ["http_router", "ws_router"]
