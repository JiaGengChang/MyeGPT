from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv
from typing import Annotated
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))

# load user modules
from models import TokenData
from variables import JWT_SECRET_KEY, JWT_SECURITY_SALT

serializer = URLSafeTimedSerializer(JWT_SECRET_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def generate_verification_token(email: Annotated[str, Depends()]) -> str:
    return serializer.dumps(email, salt=JWT_SECURITY_SALT)

def confirm_verification_token(token: Annotated[TokenData, Depends(oauth2_scheme)], expiration=3600) -> str:
    try:
        email = serializer.loads(token.payload, salt=JWT_SECURITY_SALT, max_age=expiration)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Invalid or expired token")
    
    return email

__all__ = [
    "generate_verification_token", 
    "confirm_verification_token"
]