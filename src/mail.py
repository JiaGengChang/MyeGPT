import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
from typing import Annotated
from fastapi import HTTPException, status, Depends
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from models import TokenData
from serialize import generate_verification_token

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=os.getenv("MAIL_PORT"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_verification_email(email: str, token: Annotated[TokenData, Depends(generate_verification_token)], app_url) -> None:
    link = os.path.join(app_url, f"verify?token={str(token.payload)}")
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