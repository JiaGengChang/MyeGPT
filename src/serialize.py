from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))

SECRET_KEY = os.environ.get("SECRET_KEY")
SECURITY_SALT = os.environ.get("SECURITY_SALT")

serializer = URLSafeTimedSerializer(SECRET_KEY)

def generate_verification_token(email: str) -> str:
    return serializer.dumps(email, salt=SECURITY_SALT)

def confirm_verification_token(token: str, expiration=3600) -> str:
    try:
        email = serializer.loads(token, salt=SECURITY_SALT, max_age=expiration)
    except Exception:
        return None
    return email