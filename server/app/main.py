import os
import json
from datetime import date

from typing import Annotated
from pydantic import BaseModel

from core.game_manager import GameManager
from core.challenge_manager import ChallengeManager
from core.websocket_manager import WebSocketManager

from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends

from services.docker_execution_service import DockerExecutionService

from sqlalchemy.orm import Session
from postgredb import models
from postgredb.database import SessionLocal, engine

# TODO: Move this to OAuth folder
from jose import JWTError, jwt  # For JWT token generation and validation
from datetime import datetime, timedelta  # For JWT token session time management
from passlib.context import CryptContext  # For password hashing

# run [openssl rand -hex 32] in terminal to generate a secret key, then paste them to .env file
# we can talk about this later when the database is properly set up
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# TODO: Remove this fake db
# db = {
#     "bao": {
#         "username": "bao",
#         "display_name": "bao dz",
#         "email": "bowdong@umass.edu",
#         "hashed_password": "$2b$12$dne0hHrrEf76YaO2dc9Swu2NfyUYxer0HXrFi8G3DHPtBwtWZXbPy",
#         "date_joined": "today",
#         "disabled": False,
#     },
#     # "minh": {
#     #     "username": "minh",
#     #     "full_name": "minh dz",
#     #     "email": "mivu@umass.edu",
#     #     "hashed_password": "",
#     #     "disabled": False,
#     # },
# }


class Token(BaseModel):
    """
    The JWT token is used to authenticate users
    It contains 3 parts:
    - Header: Contains the type of token and the hashing algorithm used
    - Payload: Contains the claims. Claims are statements about an entity (typically, the user) and additional data.
    - Signature: Contains the signature of the token that can be used to verify that the sender of the JWT is who it says it is and to ensure that the message wasn't changed along the way.

    Below is the definition of the Token class, which is used to handle auth
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Store data of the username after extracting it from the JWT token (decoding it)
    """

    username: str | None = None


class User(BaseModel):
    """
    defining template for the request body for the user data endpoints

    """

    username: str
    display_name: str
    email: str | None = None
    date_joined: date
    disabled: bool | None = None


# inherit from User class to add password field
class UserInDB(User):
    """
    We don't want to expose hashed_password to the client side, so we create a new class UserInDB that inherits from User and adds hashed_password field
    """

    password: str


# pwd_context use for password hashing and manage hashing algorithm
# schemes=["bcrypt"] defines bcrypt hashing algorithm
# deprecated="auto" library will auto upgrade to a more secure algo if older scheme is detected
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2: standard securing access to APIs
# Password Bearers: scheme specifically allows clients to obtain a token by sending username and password
# "token": path to endpoint where client will request a token
# client will send this in `Authorization: Bearer <token>` header with every request to access protected resources
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    """
    Verify the password entered by the user with the hashed password stored in the database
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    Hash the password before storing it in the database
    """
    return pwd_context.hash(password)


def get_user(db: Session, username: str):
    """
    Get the user from the database
    """
    # if username in db:
    #     user_dict = db[username]
    #     return UserInDB(
    #         **user_dict
    #     )  # an extended version of User class with hashed_password field

    return db.query(models.Users).filter(models.Users.username == username).first()


# Reuse the same database management logic in all routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticate_user(db: Session, username: str, password: str):
    """
    Authenticate the user by checking if the username exists in the database and the password matches
    """
    user = get_user(db, username)
    # Checking if user exist
    if not user:
        return False
    # Validating password
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, exprires_delta: timedelta | None = None):
    """
    Create a JWT token that expires in 30 minutes
    @param data: a dictionary that contains the data we want to include in the JWt payload
    @param exprires_delta: optional parameter that allows us to specify how long th token should be valid.
                           If we don't specify, the token will be valid for 15 minutes
    """
    to_encode = data.copy()
    if exprires_delta:
        expire = datetime.utcnow() + exprires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})  # update the payload with the expiration time
    encoded_jwt = jwt.encode(
        to_encode, SECRET_KEY, algorithm=ALGORITHM
    )  # return encoded JWT as a string
    return encoded_jwt


## Create an Access Token based on Login Data
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    - Get the current user by decoding the JWT token
    - The depends on oauth2_scheme: whenever the function get_current_user is called,
    FastAPI will run the function oauth2_scheme to get the token from the request headers
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # decode the token using the secret key
        username: str = payload.get("sub")  # get the username from the payload
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)  # create a TokenData object
    except JWTError:
        raise credentials_exception

    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    """
    - Check if the user is active
    - The depends on get_current_user: whenever the function get_current_active_user is called,
    FastAPI will run the function get_current_user to get the current user
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


app = FastAPI()  # Initialize FastAPI app


@app.post(
    "/token", response_model=Token
)  # FastAPI will validate, serialize, and filter the data
# (noticed the return of this function is the same as Model Token!)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Get the access token by passing the username and password
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    print("how about this")
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print("till this point")

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


# pwd = get_password_hash("baodz")
# print("minhdz", pwd)


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


# Defining template for the request body for the create-room and join-room endpoints
class PlayerJoin(BaseModel):
    player_name: str


# defining template for the request body for the user data endpoints
# class Users(BaseModel):
#     username: str
#     display_name: str
#     password: str
#     email: str
#     date_joined: str


def get_user_by_username(username: str, db: Session):
    return db.query(models.Users).filter(models.Users.username == username).first()


db_dependency = Annotated[Session, Depends(get_db)]


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
