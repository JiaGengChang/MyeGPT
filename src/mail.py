import os
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

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

async def send_verification_email(email: str, token: str, http_prefix: str = "http://localhost:8000"):
    link = f"{http_prefix}/verify?token={token}"
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Dear MyeGPT User,\n\nPlease click this link to verify your account: {link}\n\nBest regards,\nMyeGPT Admin",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
