import os
import jwt
from datetime import timedelta
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import asyncio 
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg

# src modules
from agent import send_init_prompt, query_agent
from models import Token, Query
from security import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY

auth_db_conn = psycopg.connect(os.environ.get("COMMPASS_AUTH_DSN"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(os.environ.get("COMMPASS_MEMORY_DB_URI")) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET","POST"],
    allow_headers=["Content-Type"],
)

app_dir = os.path.dirname(os.path.abspath(__file__))
graph_folder = os.path.join(app_dir, 'graph')
os.makedirs(graph_folder, exist_ok=True)
static_dir = os.path.join(app_dir, 'static')
templates_dir = os.path.join(app_dir, 'templates')
result_folder = os.path.join(app_dir, 'result')
os.makedirs(result_folder, exist_ok=True)

app.mount("/result", StaticFiles(directory=result_folder), name="result") # serve csv files
app.mount("/graph", StaticFiles(directory=graph_folder), name="graph") # serve plotted graphs
app.mount("/static", StaticFiles(directory=static_dir), name="static") # serve css/js files
app.mount("/templates", StaticFiles(directory=templates_dir), name="templates") # serve html files

# "gate" to ensure model first receives init prompt
app.state.init_prompt_done = asyncio.Event()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Routes

@app.get("/")
async def root():
    return FileResponse("templates/index.html")


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = authenticate_user(auth_db_conn, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")


# triggered by login form submission
@app.post("/redirect")
async def serve_homepage(request: Request, token: Token = Depends(login_for_access_token)):
    response = FileResponse("templates/app.html")
    response.set_cookie(
    key="access_token",
    value=token.access_token,
    httponly=False,
    secure=False,
    samesite="strict",
    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    username = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    app.state.username = username
    app.state.client_ip = request.client.host
    if not app.state.init_prompt_done.is_set():
        asyncio.create_task(send_init_prompt(app))
    return response


# retrieve response to init prompt
@app.post("/api/init")
async def get_init_response():
    await app.state.init_prompt_done.wait()
    return JSONResponse({
        "message": app.state.init_response,
        "username": app.state.username,
        "client_ip": app.state.client_ip
    })


# handle chat requests
@app.post("/api/ask")
async def ask(query: Query, token: Token = Depends(oauth2_scheme)):
    await app.state.init_prompt_done.wait()
    def generate_response():
        for chunk in query_agent(query.user_input):
            yield chunk
    return StreamingResponse(generate_response(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
    )