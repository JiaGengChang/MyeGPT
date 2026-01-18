import jwt
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
from fastapi import HTTPException
from psycopg import sql
from psycopg import connect as pconnect
from models import UserInDB
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone


SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 120

password_hash = PasswordHash.recommended()

def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def get_user(dbconn, username: str):
    with dbconn.cursor() as cur:
        query = sql.Composed([sql.SQL("SELECT username, email, hashed_password FROM auth.users WHERE username = "), sql.Literal(username)])
        cur.execute(query)
        row = cur.fetchone()
        if row:
            return UserInDB(username=row[0], email=row[1], hashed_password=row[2])


def authenticate_user(dbconn, username: str, password: str):
    user = get_user(dbconn, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_token(token: str):
    if token == os.environ.get("API_BYPASS_TOKEN"):
        # assumes the existence of username called "admin"
        return "admin"
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Token validation error: " + str(e))


def validate_user(username: str):
    client_db_conn = pconnect(os.environ.get("COMMPASS_DSN"))
    with client_db_conn.cursor() as cur:
        try:
            cur.execute("SELECT * FROM auth.users WHERE username = %s", (username,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail=f"User {username} does not exist")
            cur.execute("SELECT * FROM auth.users WHERE username = %s AND is_verified", (username,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=401, detail=f"User {username} is not verified")
        except Exception as e:
            raise HTTPException(status_code=500, detail="User validation error: " + str(e))