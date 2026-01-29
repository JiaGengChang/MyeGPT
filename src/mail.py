import os
from typing import Annotated
from fastapi import HTTPException, status, Depends
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

# user modules
from models import TokenData
from serialize import generate_verification_token
from variables import MAIL_USERNAME, MAIL_PASSWORD, MAIL_SERVER, SERVER_BASE_URL

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_USERNAME,
    MAIL_PORT=587,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_verification_email(email: str, token: Annotated[TokenData, Depends(generate_verification_token)]) -> None:
    link = os.path.join(SERVER_BASE_URL, f"verify?token={str(token.payload)}")
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Dear MyeGPT User,\n\nPlease click this link to verify your account: {link}\n\nBest regards,\nMyeGPT Admin",
        subtype=MessageType.plain
    )
    try:
        fm = FastMail(conf)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create email client. Error: " + str(e))
    
    # expect exceptions will be raised by aiosmtplib if recipient does not exist
    try:
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to send verification email to address {email}. Error: " + str(e))
    
__all__ = [
    "send_verification_email"
]