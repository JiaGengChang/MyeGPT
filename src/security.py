import jwt
import os
from fastapi import HTTPException, status, Request
import psycopg
from psycopg import sql
from models import Token, UserInDB
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone

# local modules
from variables import API_BYPASS_TOKEN, COMMPASS_AUTH_DSN, JWT_SECRET_KEY

ACCESS_TOKEN_EXPIRE_MINUTES = 120

password_hash = PasswordHash.recommended()

def _verify_password(plain_password, hashed_password) -> bool:
    if plain_password=="":
        raise HTTPException(status_code=400, detail="Plain password is empty")
    if hashed_password=="":
        raise HTTPException(status_code=500, detail="Hashed password is empty")
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    if password=="":
        raise HTTPException(status_code=400, detail="Password is empty")
    return password_hash.hash(password)


# retrieve an existing user
def _get_user(username: str) -> UserInDB:
    
    if username=="":
        raise HTTPException(status_code=400, detail="Username is empty")
    
    with psycopg.connect(COMMPASS_AUTH_DSN) as conn:
        with conn.cursor() as cur:
            try:
                query = sql.Composed([sql.SQL("SELECT username, email, hashed_password, is_verified FROM auth.users WHERE username = "), sql.Literal(username)])
                cur.execute(query)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"SQL query on auth DB failed. Error: " + str(e))
            row = cur.fetchone()
            try:
                user = UserInDB(username=row[0], email=row[1], hashed_password=row[2], is_verified=row[3])
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        
        return user


def authenticate_user(username: str, password: str) -> UserInDB:
    try:
        user = _get_user(username)
    except HTTPException as http_e:
        raise http_e
    try:
        is_password_correct = _verify_password(password, user.hashed_password)
    except HTTPException as http_e:
        raise http_e
    
    if not is_password_correct:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email is not verified")

    return user


def create_bearer_token(data: dict, expires_delta: timedelta | None = None) -> Token:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm='HS256')
    except Exception as e:
        raise HTTPException(status_code=500, detail="Token generation failed. Error: " + str(e))
    
    bearer_token = Token(access_token=encoded_jwt, token_type="bearer")
    
    return bearer_token


def validate_token_str(token_str: str) -> UserInDB:
    if token_str == API_BYPASS_TOKEN:
        # assumes the existence of username called "admin"
        return _get_user("admin")
    
    try:
        data = jwt.decode(token_str, JWT_SECRET_KEY, algorithms=['HS256'])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token. Wrong format. Error: " + str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Token validation failed. Error: " + str(e))
    
    username = data.get("sub")

    if username == "":
        raise HTTPException(status_code=401, detail="Invalid token: missing username")
    
    return _get_user(username)


# ensure same site origin, prevents scraping
def validate_headers(request: Request) -> None:
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
__all__ = [
    "authenticate_user",
    "validate_token_str",
    "validate_headers",
    "create_bearer_token",
    "get_password_hash",
]