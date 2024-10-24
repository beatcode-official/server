import os
import sys
import json

from pydantic import BaseModel
from typing import Annotated

from core.challenge_manager import ChallengeManager
from core.game_manager import GameManager
from core.websocket_manager import WebSocketManager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware

from services.docker_execution_service import DockerExecutionService

from postgredb import models
from postgredb.database import SessionLocal, engine
from sqlalchemy.orm import Session

app = FastAPI()  # Initialize FastAPI app
models.Base.metadata.create_all(bind=engine)  # Create tables in the database
## TODO: Please create a database in pgAdmin called Beatcode to really avoid errors

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Allows all origins - Let's be honest, this is too dangerous! And allows origin and credentials cannot be both * and true at the same time
    allow_credentials=True,  # Allows browser to include credentials (like cookies, HTTP authentication, or client-side SSL certificates) when making cross-origin request
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize managers and services
challenge_manager = ChallengeManager("../database/database.json")
websocket_manager = WebSocketManager()
docker_execution_service = DockerExecutionService()
game_manager = GameManager(
    challenge_manager, websocket_manager, docker_execution_service
)


# Defining template for the request body for the create-room and join-room endpoints
class PlayerJoin(BaseModel):
    player_name: str


# defining template for the request body for the user data endpoints
class Users(BaseModel):
    username: str
    display_name: str
    password: str
    email: str
    date_joined: str


# Reuse the same database management logic in all routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


@app.post("/register/")
async def register(user: Users, db: db_dependency):
    """
    Sample request body:
    {
        "username": "bao",
        "display_name": "baodz",
        "password": "lonton",
        "email": "minhdz@gmail.com",
        "date_joined": "today"
    }
    """
    db_user = models.Users(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return user


@app.post("/delete-all-users/")  # TODO: For testing purposes only
async def delete_all_users(db: db_dependency):
    try:
        db.query(models.Users).delete()
        db.commit()
        return {"message": "All users deleted successfully"}
    except Exception as e:
        db.rollback()
        return {"message": str(e)}


@app.post("/api/create-room")
async def create_room(
    player: PlayerJoin,
):  # ensure incoming request containing player_name
    room_info = game_manager.create_room(player.player_name)
    return room_info


@app.post("/api/join-room/{room_code}")
async def join_room(room_code: str, player: PlayerJoin):
    try:
        room_info = game_manager.join_room(room_code, player.player_name)
        return room_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Allow for real-time communication between players in the same room
@app.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    # Check if room exists and player is in the room
    if (
        room_code not in game_manager.rooms
        or player_id not in game_manager.rooms[room_code]["players"]
    ):
        await websocket.close()
        return

    await websocket_manager.connect(websocket, room_code, player_id)
    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)  # TODO: How do you know the format of this data?

            try:
                if event["event"] == "start_game":
                    await game_manager.start_game(room_code, player_id)
                elif event["event"] == "submit_code":
                    await game_manager.submit_code(
                        room_code, player_id, event["event_data"]["code"]
                    )
            except Exception as e:
                await websocket.send_text(
                    json.dumps({"event": "error", "event_data": {"error_msg": str(e)}})
                )
    except WebSocketDisconnect:
        await websocket_manager.disconnect(room_code, player_id)
    except Exception as e:
        print(e)
        await websocket_manager.disconnect(room_code, player_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
