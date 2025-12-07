import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio 
import psycopg
import uuid

# src modules
from agent import send_init_prompt, query_agent
from models import Query

auth_db_conn = psycopg.connect(os.environ.get("COMMPASS_AUTH_DSN"))

app = FastAPI()

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

# Route(s)
# triggered by submission of query
@app.post("/api/ask")
async def ask(query: Query):
    app.state.username = uuid.uuid4().hex
    app.state.model_id = os.environ.get("MODEL_ID")
    app.state.embeddings_model_id = os.environ.get("EMBEDDINGS_MODEL_ID")
    await send_init_prompt(app)

    def generate_response():
        for chunk in query_agent(query.user_input):
            yield chunk
    return StreamingResponse(generate_response(), media_type="application/json")

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    assert load_dotenv(os.path.join(os.path.dirname(__file__),'.env'))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
    )