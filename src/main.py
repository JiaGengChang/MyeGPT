import os
import jwt
from datetime import timedelta
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import asyncio 
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg
from typing import Annotated

# src modules
from agent import send_init_prompt, query_agent
from models import Token, Query, UserCreate, UserInDB
from security import get_password_hash, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from mail import send_verification_email
from serialize import generate_verification_token, confirm_verification_token

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
scripts_dir = os.path.join(app_dir, 'static', 'scripts')
templates_dir = os.path.join(app_dir, 'templates')
result_folder = os.path.join(app_dir, 'result')
os.makedirs(result_folder, exist_ok=True)

app.mount("/result", StaticFiles(directory=result_folder), name="result") # serve csv files
app.mount("/graph", StaticFiles(directory=graph_folder), name="graph") # serve plotted graphs
app.mount("/static", StaticFiles(directory=static_dir), name="static") # serve css/js files
app.mount("/scripts", StaticFiles(directory=scripts_dir), name="scripts") # serve css/js files
app.mount("/templates", StaticFiles(directory=templates_dir), name="templates") # serve html files

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Routes

# serve landing page
@app.get("/")
async def root():
    return FileResponse(f"{app_dir}/templates/index.html")


# not triggered, here for OpenAPI compliance
@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
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


# triggered by registration form submission
@app.post("/register")
async def register_with_form(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    confirm_password = form.get("confirm-password")
    email = form.get("email", "").strip()
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not (username and email and password):
        raise HTTPException(status_code=400, detail="All fields are required")
    new_user = UserCreate(username=username, password=password, email=email)
    response = await register_user(new_user)
    return response


# not triggered directly
# called by register_with_form
# for use within swagger UI
@app.post("/api/register")
async def register_user(user: UserCreate):
    assert os.environ.get("SERVER_BASE_URL"), "Env. variable SERVER_BASE_URL is missing"
    hashed_password = get_password_hash(user.password)
    with auth_db_conn.cursor() as cur:
        try:
            user_email = user.email if user.email.strip().__len__() > 0 else None
            # FIXME - do not allow delete if account was created within X minutes
            cur.execute("DELETE FROM auth.users WHERE email = %s AND is_verified = FALSE", (user_email,))
            auth_db_conn.commit()
            cur.execute(
            "INSERT INTO auth.users (username, email, hashed_password) VALUES (%s, %s, %s)",
            (user.username, user_email, hashed_password)
            )
            auth_db_conn.commit()
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=400, detail="Username or email is already taken.")

    # try:
    token = generate_verification_token(user_email)
    await send_verification_email(user_email, token, os.environ.get("SERVER_BASE_URL"))
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail="Failed to send verification email. Error: " + str(e))

    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/pending.html") as script_file:
        html = html_file.read()
        script = script_file.read()
        response = HTMLResponse(html + script)
        response.headers["X-User-Email"] = user_email

    return response


# triggered by clicking the link in verification email
@app.get("/verify")
def verify_email(token: str):
    email = confirm_verification_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    with auth_db_conn.cursor() as cur:
        cur.execute("SELECT username, email, hashed_password, is_verified FROM auth.users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        user = UserInDB(username=row[0], email=row[1], hashed_password=row[2], is_verified=row[3])
        if user.is_verified:
            raise HTTPException(status_code=400, detail="Account already verified.")
        cur.execute("UPDATE auth.users SET is_verified = TRUE WHERE email = %s", (email,))
        auth_db_conn.commit()

    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/verified.html") as script_file:
        html = html_file.read()
        script = script_file.read()
        response = HTMLResponse(html + script)
        response.headers["Refresh"] = "4; url=/"

    return response


# triggered by clicking delete account button
# this will remove user from auth.users and the conversation history
@app.delete("/api/delete_account")
async def delete_account(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        await erase_memory(token)
    except Exception as e:
        raise e
    username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("DELETE FROM auth.users WHERE username = %s", (username,))
            auth_db_conn.commit()
        except:
            raise HTTPException(status_code=500, detail="Failed to delete account")
    return JSONResponse({"message": "Account deleted successfully."})


# triggered by clicking erase memory button
# this will remove conversation history
@app.delete("/api/erase_memory")
async def erase_memory(token: Annotated[str, Depends(oauth2_scheme)]):
    username = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("DELETE FROM commpass_schema.checkpoints WHERE thread_id = %s", (username,))
            cur.execute("DELETE FROM commpass_schema.checkpoint_writes WHERE thread_id = %s", (username,))
            cur.execute("DELETE FROM commpass_schema.checkpoint_blobs WHERE thread_id = %s", (username,))
            auth_db_conn.commit()
        except:
            raise HTTPException(status_code=500, detail="Failed to erase memory")
    return JSONResponse({"message": "Memory erased successfully."})



# triggered by login form submission
@app.post("/app")
async def serve_homepage(request: Request, token: Annotated[Token, Depends(login_for_access_token)]):
    app.state.init_prompt_done = asyncio.Event()
    response = FileResponse(f"{app_dir}/templates/app.html")
    try:
        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=False,
            secure=False,
            samesite="strict",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to set cookie. Error: " + str(e))
    try:
        # "gate" to ensure model first receives init prompt
        username = jwt.decode(token.access_token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        app.state.username = username
        app.state.client_ip = request.client.host
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode token. Error: " + str(e))
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("SELECT email FROM auth.users WHERE username = %s", (username,))
            row = cur.fetchone()
            app.state.email = row[0] if row and row[0] else None
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to fetch user email. Error: " + str(e))
    
    if not app.state.init_prompt_done.is_set():
        asyncio.create_task(send_init_prompt(app))
    return response


# triggered by /app
@app.post("/api/init")
async def get_init_response():
    await app.state.init_prompt_done.wait()
    return JSONResponse({
        "message": app.state.init_response,
        "username": app.state.username,
        "email": app.state.email,
        "client_ip": app.state.client_ip
    })


# triggered by submission of query
@app.post("/api/ask")
async def ask(query: Query, token: Annotated[str, Depends(oauth2_scheme)]):
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