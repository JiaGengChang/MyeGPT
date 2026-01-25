from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv
from typing import Annotated
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))

from models import TokenData

SECRET_KEY = os.environ.get("SECRET_KEY")
SECURITY_SALT = os.environ.get("SECURITY_SALT")

serializer = URLSafeTimedSerializer(SECRET_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def generate_verification_token(email: Annotated[str, Depends()]) -> str:
    return serializer.dumps(email, salt=SECURITY_SALT)

def confirm_verification_token(token: Annotated[TokenData, Depends(oauth2_scheme)], expiration=3600) -> str:
    try:
        email = serializer.loads(token.payload, salt=SECURITY_SALT, max_age=expiration)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Invalid or expired token")
    
    return email

__all__ = [
    "generate_verification_token", 
    "confirm_verification_token"
]