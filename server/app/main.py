import json

from core.challenge_manager import ChallengeManager
from core.game_manager import GameManager
from core.websocket_manager import WebSocketManager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.docker_execution_service import DockerExecutionService

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize managers and services
challenge_manager = ChallengeManager("../database/database.json")
websocket_manager = WebSocketManager()
docker_execution_service = DockerExecutionService()
game_manager = GameManager(challenge_manager, websocket_manager, docker_execution_service)


class PlayerJoin(BaseModel):
    player_name: str


@app.post("/api/create-room")
async def create_room(player: PlayerJoin):
    room_info = game_manager.create_room(player.player_name)
    return room_info


@app.post("/api/join-room/{room_code}")
async def join_room(room_code: str, player: PlayerJoin):
    try:
        room_info = game_manager.join_room(room_code, player.player_name)
        return room_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    # Check if room exists and player is in the room
    if room_code not in game_manager.rooms or player_id not in game_manager.rooms[room_code]["players"]:
        await websocket.close()
        return

    await websocket_manager.connect(websocket, room_code, player_id)
    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)

            try:
                if event["event"] == "start_game":
                    await game_manager.start_game(room_code, player_id)
                elif event["event"] == "submit_code":
                    await game_manager.submit_code(room_code, player_id, event["event_data"]["code"])
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "event": "error",
                    "event_data": {
                        "error_msg": str(e)
                    }
                }))
    except WebSocketDisconnect:
        await websocket_manager.disconnect(room_code, player_id)
    except Exception as e:
        print(e)
        await websocket_manager.disconnect(room_code, player_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
