from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    payload: str | None = None


class _User(BaseModel):
    username: str
    email: str | None = None


class UserInDB(_User):
    hashed_password: str
    is_verified: bool = False


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class Query(BaseModel):
    user_input: str


__all__ = [
    "Token", "TokenData", "Query", "UserCreate", "UserInDB"
]