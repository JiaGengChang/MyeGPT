import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio 

# src modules
from agent import send_init_prompt, query_agent

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
result_folder = os.path.join(app_dir, 'result')
os.makedirs(result_folder, exist_ok=True)

app.mount("/result", StaticFiles(directory=result_folder), name="result") # serve csv files
app.mount("/graph", StaticFiles(directory=graph_folder), name="graph") # serve plotted graphs
app.mount("/static", StaticFiles(directory=static_dir), name="static") # serve static files

# "gate" to ensure model first receives init prompt
app.state.init_prompt_done = asyncio.Event()

# Serve landing page
@app.get("/")
async def serve_frontend():
    response = FileResponse("static/index.html")
    # Create task to send init prompt
    if not app.state.init_prompt_done.is_set():
        asyncio.create_task(send_init_prompt(app))
    return response

# retrieve response to init prompt
@app.post("/api/init")
async def get_init_response():
    await app.state.init_prompt_done.wait()
    return PlainTextResponse(app.state.init_response)

class Query(BaseModel):
    user_input: str

# handle chat requests
@app.post("/api/ask")
async def ask(query: Query):
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