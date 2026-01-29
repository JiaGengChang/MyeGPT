import os
import psycopg
import asyncio
from typing import Annotated
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, HTMLResponse

# src modules
from agent import handle_invalid_chat_history, send_init_prompt, query_agent
from mail import send_verification_email
from models import Token, TokenData, Query, UserCreate, UserInDB
from security import get_password_hash, authenticate_user, create_bearer_token, validate_token_str, validate_headers
from serialize import generate_verification_token, confirm_verification_token
from variables import COMMPASS_AUTH_DSN, COMMPASS_DSN, COMMPASS_MEMORY_DB_URI, MODEL_ID

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(COMMPASS_MEMORY_DB_URI) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        yield

app = FastAPI(lifespan=lifespan)

# update FastAPI app state with user info and model IDs
def update_app_state(user: UserInDB) -> None:
    global app
    # user must be verified to exist by now
    app.state.username = user.username
    app.state.email = user.email
    app.state.model_id = MODEL_ID
    app.state.embeddings_model_id = os.environ.get("EMBEDDINGS_MODEL_ID")


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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Routes

# serve landing page
@app.get("/")
async def root(request: Request) -> FileResponse:
    
    print(request.headers)

    response = FileResponse(f"{app_dir}/templates/index.html")

    return response


# not triggered, here for OpenAPI compliance
@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request
) -> Token:
    print(request.headers)

    validate_headers(request)

    try:
        user = authenticate_user(form_data.username, form_data.password)
    except HTTPException as http_e:
        raise http_e
    
    access_token = create_bearer_token(data={"sub": user.username})

    # add user info to app.state
    update_app_state(user)

    return access_token


# triggered by registration form submission
@app.post("/register")
async def register_with_form(request: Request) -> HTMLResponse:
    
    validate_headers(request)

    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    confirm_password = form.get("confirm-password")
    email = form.get("email", "").strip()
    
    if password != confirm_password:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="Passwords do not match")
    
    if not (username and email and password):
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="All fields are required")
    
    new_user = UserCreate(username=username, password=password, email=email)
    
    response = await register_user(new_user, request)
    
    return response


# not triggered directly
# called by register_with_form
# for use within swagger UI
@app.post("/api/register")
async def register_user(user: Annotated[UserCreate, Depends()], request: Request) -> HTMLResponse:
    hashed_password = get_password_hash(user.password)
    auth_db_conn = psycopg.connect(COMMPASS_AUTH_DSN)
    with auth_db_conn.cursor() as cur:
        user_email = user.email if user.email.strip().__len__() > 0 else None
        try:
            cur.execute("DELETE FROM auth.users WHERE (username = %s OR email = %s) AND is_verified = FALSE", (user.username, user_email))
            cur.execute("INSERT INTO auth.users (username, email, hashed_password) VALUES (%s, %s, %s)",(user.username, user_email, hashed_password))
            auth_db_conn.commit()
        except psycopg.errors.UniqueViolation:
            auth_db_conn.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered")
        except Exception as e_userdb:
            auth_db_conn.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user. Error: " + str(e_userdb))

    token = TokenData(payload=generate_verification_token(user_email))

    await send_verification_email(user_email, token)

    # redirect user to pending verification page
    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/pending.html") as f:
        html = html_file.read()
        script = f.read()
        response = HTMLResponse(html + script)
        response.headers["X-User-Email"] = user_email

    return response


# triggered by clicking the link in verification email, expires in 5 minutes
@app.get("/verify")
def verify_email(token: str) -> HTMLResponse:
    
    # raises 408 if token is invalid or expired
    email = confirm_verification_token(TokenData(payload=token), expiration=300)
    
    with psycopg.connect(COMMPASS_AUTH_DSN) as conn:

        # verify user with given email exists
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT username FROM auth.users WHERE email = %s", (email,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with email {email} not found. Please register first.")
            except Exception as e_userdb:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Query on users DB failed. Error: " + str(e_userdb))    
        
        # verify the incoming user's email
        with conn.cursor() as cur:
            try:
                cur.execute("UPDATE auth.users SET is_verified = TRUE WHERE email = %s", (email,))
                conn.commit()
            except Exception as e_verify:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify account. Error: " + str(e_verify))

    # redirect user to homepage
    with open(f"{app_dir}/templates/redirect.html") as html_file, open(f"{app_dir}/templates/verified.html") as f:
        html = html_file.read()
        script = f.read()
        response = HTMLResponse(html + script)
        response.headers["Refresh"] = "3; url=/"

    return response


# triggered by clicking delete account button
# this will remove user from auth.users and the conversation history
@app.delete("/api/delete_account")
async def delete_account(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> HTMLResponse:
    print(request.headers)

    # ensure same origin request
    validate_headers(request)
    
    # ensure token is valid and user exists in db
    user = validate_token_str(token_str)
    
    # clear conversation history of user
    _ = await erase_memory(token_str, request)

    # delete user from db
    with psycopg.connect(COMMPASS_AUTH_DSN) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM auth.users WHERE username = %s", (user.username,))
                conn.commit()
            except Exception as e_userdb:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error in user DB. Failed to delete account. Error: " + str(e_userdb))

    response = JSONResponse({"message": "Account deleted successfully."})
    
    # delete bearer token cookie
    try:
        response.delete_cookie(key="access_token")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete cookie. Error: " + str(e))

    return response


# triggered by clicking erase memory button
# this will remove conversation history
@app.delete("/api/erase_memory")
async def erase_memory(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> JSONResponse:
    print(request.headers)
    
    validate_headers(request)
    
    user = validate_token_str(token_str)

    with psycopg.connect(COMMPASS_MEMORY_DB_URI) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM checkpoints.checkpoints WHERE thread_id = %s", (user.username,))
                cur.execute("DELETE FROM checkpoints.checkpoint_writes WHERE thread_id = %s", (user.username,))
                cur.execute("DELETE FROM checkpoints.checkpoint_blobs WHERE thread_id = %s", (user.username,))
                conn.commit()
            except Exception as e_memorydb:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to erase memory. Error: " + str(e_memorydb))
    return JSONResponse({"message": "Memory erased successfully."})



# triggered by login form submission
@app.post("/app")
async def serve_homepage(token: Annotated[Token, Depends(login_for_access_token)], request: Request) -> FileResponse:
    print(request.headers)
    
    validate_headers(request)
    
    app.state.init_prompt_done = asyncio.Event()
    
    if not app.state.init_prompt_done.is_set():
        asyncio.create_task(send_init_prompt(app))
    
    response = FileResponse(f"{app_dir}/templates/app.html")
    
    try:
        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=False,
            secure=False,
            samesite="strict",
            max_age=7200, # 2 hours
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set cookie. Error: " + str(e))

    return response

# triggered by /app
@app.post("/api/init")
async def get_init_response(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> JSONResponse:
    print(request.headers)

    validate_headers(request)

    user = validate_token_str(token_str)
    
    update_app_state(user)

    # ensure init prompt is sent
    if not hasattr(app.state, "init_prompt_done"):
        token = Token(access_token=token_str, token_type="bearer")
        await serve_homepage(token, request)
    
    # await initialization
    if not app.state.init_prompt_done.is_set():
        try:
            # send init prompt from agent.py
            await app.state.init_prompt_done.wait()
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize agent. Error: " + str(e))

    return JSONResponse({
        "message": app.state.init_response,
        "username": app.state.username,
        "email": app.state.email,
        "model_id": app.state.model_id,
        "embeddings_model_id": app.state.embeddings_model_id,
    })


# triggered by submission of query
@app.post("/api/ask")
async def ask(query: Query, token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> StreamingResponse:
    print(request.headers)

    validate_headers(request)
    
    # ensure token is valid and user exists in DB
    validate_token_str(token_str)

    # ensure init prompt is sent
    if not hasattr(app.state, "init_prompt_done"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent not initialized.")
    
    # await initialization
    await app.state.init_prompt_done.wait()

    def generate_response():
        yield from query_agent(app, query.user_input)
        
    return StreamingResponse(generate_response(), media_type="text/plain")


# readiness probe
# returns 200 if all checks pass
# otherwise returns 500
@app.post("/ready")
async def ready(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> JSONResponse:

    print(request.headers)

    validate_headers(request)

    # validate token to allow readiness probing
    # and test token and user validation
    _ = validate_token_str(token_str)

    # test commpass db connection
    with psycopg.connect(COMMPASS_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pg_tables WHERE schemaname = 'public' LIMIT 1")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Commpass database connection failed")
    
    # test auth db connection
    with psycopg.connect(COMMPASS_AUTH_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM auth.users LIMIT 1;")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User database connection failed")

    # test memory db connection
    with psycopg.connect(COMMPASS_MEMORY_DB_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pg_tables WHERE schemaname = 'checkpoints' LIMIT 1")
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Memory database connection failed")

    return JSONResponse({"status": "ok"})

@app.post("/api/fix_history")
async def fix_history(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> JSONResponse:
    dummy_exception = Exception("bypass")

    response_code = await handle_invalid_chat_history(app, dummy_exception)

    return JSONResponse({"response": response_code, "status": "ok"})
    

@app.get("/api/usage_metadata")
async def usage_metadata(token_str: Annotated[str, Depends(oauth2_scheme)], request: Request) -> JSONResponse:
    print(request.headers)

    validate_headers(request)

    # validate token to allow usage metadata access
    _ = validate_token_str(token_str)

    try:
        return JSONResponse({"usage_metadata": app.state.usage_metadata, "status": "ok"})
    
    except AttributeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No usage metadata found.")

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
    )