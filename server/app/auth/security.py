from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends

from jose import JWTError, jwt  # For JWT token generation and validation
from datetime import datetime, timedelta  # For JWT token session time management
from passlib.context import CryptContext  # For password hashing

from sqlalchemy.orm import Session

from postgredb import models
from postgredb.database import get_db

from schemas import TokenData, UserInDB

from config import ALGORITHM, SECRET_KEY

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


def get_user_by_username(username: str, db: Session):
    return db.query(models.Users).filter(models.Users.username == username).first()
