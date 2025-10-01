import os
import jwt
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
from psycopg import sql
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