import json

from typing import Annotated

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends

from datetime import timedelta  # For JWT token session time management

from services.docker_execution_service import DockerExecutionService

from sqlalchemy.orm import Session

from postgredb import models
from postgredb.database import engine, get_db

from core.game_manager import GameManager
from core.challenge_manager import ChallengeManager
from core.websocket_manager import WebSocketManager

from schemas import Token, User, UserInDB, PlayerJoin
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from auth.security import (
    authenticate_user,
    create_access_token,
    get_user_by_username,
    get_password_hash,
    get_current_active_user,
)

app = FastAPI()  # Initialize FastAPI app


## TODO for all: Please create a database in pgAdmin4 called Beatcode to really avoid errors
models.Base.metadata.create_all(bind=engine)  # Create tables in the database

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


db_dependency = Annotated[Session, Depends(get_db)]


## Endpoints definition
@app.post("/register/")
async def register(user: UserInDB, db: db_dependency):
    """
    @param user: FastAPI automatically deserializes the request body into the User Pydantic model
    @param db: FastAPI uses dependency injection to provide the database session
    Sample request body:
    {
        "username": "bao",
        "display_name": "baoszai",
        "hashed_password": "lonton",
        "email": "minhdz@gmail.com",
        "date_joined": "today",
        "disabled": false
    }
    """
    # Check if the username already exists
    if get_user_by_username(user.username, db):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password before storing it in the database
    hashed_password = get_password_hash(user.password)

    # Create a dictionary from user data and update it with the hashed password
    user_data = user.model_dump()
    user_data.update({"hashed_password": hashed_password})
    del user_data["password"]

    # Create a new user in the database
    db_user = models.Users(**user_data)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return user


@app.post(
    "/delete-all-users/"
)  # TODO: For testing purposes only. This function will kill all users in the database. DELETE later
async def delete_all_users(db: db_dependency):
    try:
        db.query(models.Users).delete()
        db.commit()
        return {"message": "All users deleted successfully"}
    except Exception as e:
        db.rollback()
        return {"message": str(e)}


@app.post(
    "/token", response_model=Token
)  # FastAPI will validate, serialize, and filter the data
# (noticed the return of this function is the same as Model Token!)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Get the access token by passing the username and password
    This equivalent to the login endpoint
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, exprires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get the user data
    """
    return current_user


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
