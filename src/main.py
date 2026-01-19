import os
import jwt
import uuid
from datetime import timedelta
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncio 
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import psycopg
from typing import Annotated

# src modules
from agent import send_init_prompt, query_agent
from models import Token, TokenData, Query, UserCreate
from security import get_password_hash, authenticate_user, create_access_token, validate_token, validate_user, patch_user_info, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
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
        return access_token


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
    
    try:
        response = await register_user(new_user)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    return response


# not triggered directly
# called by register_with_form
# for use within swagger UI
@app.post("/api/register")
async def register_user(user: UserCreate) -> HTMLResponse:
    assert os.environ.get("SERVER_BASE_URL"), "Env. variable SERVER_BASE_URL is missing"
    hashed_password = get_password_hash(user.password)
    with auth_db_conn.cursor() as cur:
        user_email = user.email if user.email.strip().__len__() > 0 else None
        try:
            cur.execute("DELETE FROM auth.users WHERE (username = %s OR email = %s) AND is_verified = FALSE", (user.username, user_email))
            cur.execute("INSERT INTO auth.users (username, email, hashed_password) VALUES (%s, %s, %s)",(user.username, user_email, hashed_password))
            auth_db_conn.commit()
        except psycopg.errors.UniqueViolation:
            auth_db_conn.rollback()
            raise HTTPException(status_code=400, detail="Username or email already registered")
        except Exception as e_unknown:
            auth_db_conn.rollback()
            raise HTTPException(status_code=400, detail="Failed to register user. Error: " + str(e_unknown))

    token = generate_verification_token(user_email)

    try:
        await send_verification_email(user_email, token, os.environ.get("SERVER_BASE_URL"))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to send verification email. Error: " + str(e))

    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/pending.html") as f:
        html = html_file.read()
        script = f.read()
        response = HTMLResponse(html + script)
        response.headers["X-User-Email"] = user_email

    return response


# triggered by clicking the link in verification email, expires in 5 minutes
@app.get("/verify")
def verify_email(token: str):
    
    # raises 400 if token is invalid or expired
    try:
        email = confirm_verification_token(token, expiration=300)
    except Exception as e:
        raise e
    
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("SELECT username, email, hashed_password, is_verified FROM auth.users WHERE email = %s", (email,))
            row = cur.fetchone()
        except Exception as e:
            raise HTTPException(status_code=400, detail="User not found. Error: " + str(e))
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("UPDATE auth.users SET is_verified = TRUE WHERE email = %s", (email,))
            auth_db_conn.commit()
        except Exception as e:
            auth_db_conn.rollback()
            raise HTTPException(status_code=400, detail="Failed to verify account. Error: " + str(e))

    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/verified.html") as script_file:
        html = html_file.read()
        script = script_file.read()
        response = HTMLResponse(html + script)
        response.headers["Refresh"] = "3; url=/"

    return response


# triggered by clicking delete account button
# this will remove user from auth.users and the conversation history
@app.delete("/api/delete_account")
async def delete_account(token: Annotated[TokenData, Depends(oauth2_scheme)], request: Request):
    print(request.headers)

    # ensure same origin request
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    # ensure token is valid
    try:
        username = validate_token(token)
    except Exception as e:
        raise HTTPException(status_code=409, detail="Failed to decode token. Error: " + str(e))
    
    # ensure user exists
    try:
        validate_user(username)
    except Exception as e:
        raise HTTPException(status_code=401, detail="User does not exist. Error: " + str(e))

    # clear conversation history of user
    try:
        await erase_memory(token)
    except Exception as e:
        raise HTTPException(status_code=500, detail="DB error. Failed to erase memory. Error: " + str(e))
    
    # delete user from db
    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("DELETE FROM auth.users WHERE username = %s", (username,))
            auth_db_conn.commit()
        except Exception as e:
            auth_db_conn.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete account. Error: " + str(e))

    return JSONResponse({"message": "Account deleted successfully."})


# triggered by clicking erase memory button
# this will remove conversation history
@app.delete("/api/erase_memory")
async def erase_memory(token: Annotated[TokenData, Depends(oauth2_scheme)], request: Request):
    print(request.headers)
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    try:
        user = validate_token(token)
    except Exception as e:
        raise e

    with auth_db_conn.cursor() as cur:
        try:
            cur.execute("DELETE FROM commpass_schema.checkpoints WHERE thread_id = %s", (user.username,))
            cur.execute("DELETE FROM commpass_schema.checkpoint_writes WHERE thread_id = %s", (user.username,))
            cur.execute("DELETE FROM commpass_schema.checkpoint_blobs WHERE thread_id = %s", (user.username,))
            auth_db_conn.commit()
        except Exception as e:
            auth_db_conn.rollback()
            raise HTTPException(status_code=500, detail="Failed to erase memory. Error: " + str(e))
    return JSONResponse({"message": "Memory erased successfully."})



# triggered by login form submission
@app.post("/app")
async def serve_homepage(request: Request, token: Annotated[Token, Depends(login_for_access_token)]):
    print(request.headers)
    
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

    # ensure token is valid and user exists in db    
    try:
        user = validate_token(TokenData(payload=token.access_token))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Failed to decode token. Error: " + str(e))
    
    # patch missing user info in app.state
    patch_user_info(app, auth_db_conn, user)
    
    if not app.state.init_prompt_done.is_set():
        asyncio.create_task(send_init_prompt(app))
    
    return response

# triggered by /app
@app.post("/api/init")
async def get_init_response(token: Annotated[TokenData, Depends(oauth2_scheme)], request: Request):
    print(request.headers)

    # ensure same origin request
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=403, detail="Access forbidden")

    # ensure token is valid and user exists in db
    try:
        user = validate_token(TokenData(payload=token))
    except Exception as e:
        raise e
    
    # patch missing user info in app.state
    patch_user_info(app, auth_db_conn, user)

    # ensure same user as app
    try:
        assert app.state.username == user.username
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token username does not match app username. Error: " + str(e))

    # ensure init prompt is sent
    if not hasattr(app.state, "init_prompt_done"):
        raise HTTPException(status_code=409, detail="Agent not initialized.")
    
    # await initialization
    if not app.state.init_prompt_done.is_set():
        try:
            # send init prompt from agent.py
            await app.state.init_prompt_done.wait()
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to initialize agent. Error: " + str(e))

    return JSONResponse({
        "message": app.state.init_response,
        "username": app.state.username,
        "email": app.state.email,
        "model_id": app.state.model_id,
        "embeddings_model_id": app.state.embeddings_model_id,
    })


# triggered by submission of query
@app.post("/api/ask")
async def ask(query: Query, token: Annotated[TokenData, Depends(oauth2_scheme)], request: Request):
    print(request.headers)

    # ensure same origin request
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    # ensure token is valid and user exists in DB
    try:
        user = validate_token(TokenData(payload=token))
    except Exception as e:
        raise e

    # ensure same user as app
    try:
        assert app.state.username == user.username
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token username does not match app username. Error: " + str(e))

    # ensure init prompt is sent
    if not hasattr(app.state, "init_prompt_done"):
        raise HTTPException(status_code=409, detail="Agent not initialized.")

    # await initialization
    await app.state.init_prompt_done.wait()

    def generate_response():
        yield from query_agent(query.user_input)
        
    return StreamingResponse(generate_response(), media_type="text/plain")


# readiness probe
# returns 200 if all checks pass
# otherwise returns 500
@app.post("/ready")
async def ready(token: Annotated[TokenData, Depends(oauth2_scheme)], request: Request):

    print(request.headers)

    # ensure same origin request
    if not request.headers.get("sec-fetch-site") == "same-origin":
        raise HTTPException(status_code=403, detail="Access forbidden")

    # validate token to allow readiness probing
    # and test token and user validation
    try:
        user = validate_token(TokenData(payload=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to decode token. Error: " + str(e))

    # test commpass db connection
    with psycopg.connect(os.environ.get("COMMPASS_DSN")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pg_tables WHERE schemaname = 'public' LIMIT 1")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="Commpass database connection failed")
    
    # test auth db connection
    with psycopg.connect(os.environ.get("COMMPASS_AUTH_DSN")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM auth.users LIMIT 1;")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="User database connection failed")

    # test memory db connection
    with psycopg.connect(os.environ.get("COMMPASS_MEMORY_DB_URI")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pg_tables WHERE schemaname = 'commpass_schema' LIMIT 1")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="Memory database connection failed")

    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
    )