from typing import Dict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        """
        Initializes the WebSocketManager with an empty dictionary to store active WebSocket connections.
        """
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, player_id: str):
        """
        Connects a WebSocket to a room with the given room code and player ID.

        Args:
            websocket (WebSocket): The WebSocket connection to connect.
            room_code (str): The room code to connect to.
            player_id (str): The player ID to connect with.
        """
        if room_code not in self.active_connections:
            self.active_connections[room_code] = {}
        self.active_connections[room_code][player_id] = websocket
        await websocket.accept()

    async def disconnect(self, room_code: str, player_id: str):
        """
        Disconnects a WebSocket from a room with the given room code and player ID.

        Args:
            room_code (str): The room code to disconnect from.
            player_id (str): The player ID to disconnect.
        """
        if room_code in self.active_connections:
            self.active_connections[room_code].pop(player_id, None)
            if not self.active_connections[room_code]:
                self.active_connections.pop(room_code, None)

    async def broadcast(self, room_code: str, message: str):
        """
        Broadcasts a message to all WebSockets in a room with the given room code.
        """
        if room_code in self.active_connections:
            for websocket in self.active_connections[room_code].values():
                await websocket.send_text(message)

    async def send(self, room_code: str, player_id: str, message: str):
        """
        Sends a message to a WebSocket in a room with the given room code and player ID.
        """
        if room_code in self.active_connections and player_id in self.active_connections[room_code]:
            await self.active_connections[room_code][player_id].send_text(message)
