import jwt
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
from fastapi import FastAPI, HTTPException
import psycopg
from psycopg import sql
from models import Token, TokenData, UserInDB
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone


SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 120

password_hash = PasswordHash.recommended()

auth_db_conn = psycopg.connect(os.environ.get("COMMPASS_AUTH_DSN"))


def _verify_password(plain_password, hashed_password):
    if plain_password=="":
        raise HTTPException(status_code=400, detail="Plain password is empty")
    if hashed_password=="":
        raise HTTPException(status_code=500, detail="Hashed password is empty")
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    if password=="":
        raise HTTPException(status_code=400, detail="Password is empty")
    return password_hash.hash(password)


# retrieve an existing user
def _get_user(dbconn, username: str) -> UserInDB:
    if username=="":
        raise HTTPException(status_code=400, detail="Username is empty")
    with dbconn.cursor() as cur:
        try:
            query = sql.Composed([sql.SQL("SELECT username, email, hashed_password FROM auth.users WHERE username = "), sql.Literal(username)])
            cur.execute(query)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL query on auth DB failed. Error: " + str(e))
        row = cur.fetchone()
        try:
            user_obj = UserInDB(username=row[0], email=row[1], hashed_password=row[2])
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"User {username} not found. Error: " + str(e))
        
        return user_obj

# silently validate user existence
def validate_user(username: str) -> None:
    try:
        _get_user(auth_db_conn, username)
    except HTTPException as http_e:
        raise http_e


def authenticate_user(dbconn, username: str, password: str) -> UserInDB:
    try:
        user = _get_user(dbconn, username)
    except HTTPException as http_e:
        raise http_e
    try:
        _verify_password(password, user.hashed_password)
    except HTTPException as http_e:
        raise http_e
    
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> Token:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    token_obj = Token(access_token=encoded_jwt, token_type="bearer")
    return token_obj


def validate_token(token: TokenData) -> UserInDB:
    if token.payload == os.environ.get("API_BYPASS_TOKEN"):
        # assumes the existence of username called "admin"
        return _get_user(auth_db_conn, "admin")
    try:
        payload = jwt.decode(token.payload, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Token validation failed. Error: " + str(e))
    if username == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    return _get_user(auth_db_conn, username)


# update FastAPI app state with user info and model IDs
def patch_user_info(app: FastAPI, auth_db_conn: psycopg.Connection, user: UserInDB) -> None:
    # user must be verified to exist by now
    if not hasattr(app.state, "username"):
        app.state.username = user.username
    if not hasattr(app.state, "email"):
        app.state.email = user.email
    if not hasattr(app.state, "model_id"):
        app.state.model_id = os.environ.get("MODEL_ID")
    if not hasattr(app.state, "embeddings_model_id"):
        app.state.embeddings_model_id = os.environ.get("EMBEDDINGS_MODEL_ID")