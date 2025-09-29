from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    payload: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None


class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class Query(BaseModel):
    user_input: str


class Question(BaseModel):
    question: str