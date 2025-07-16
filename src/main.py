import os
import uuid
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import ssl 

# src modules
from agent import query_agent

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain(os.environ.get('CERT_FILE'), keyfile=os.environ.get('KEY_FILE'))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_dir = os.path.dirname(os.path.abspath(__file__))
graph_folder = os.path.join(app_dir, 'graph')
os.makedirs(graph_folder, exist_ok=True)
json_folder = os.path.join(app_dir, 'json')
os.makedirs(json_folder, exist_ok=True)
static_dir = os.path.join(app_dir, 'static')

app.mount("/graph", StaticFiles(directory=graph_folder), name="graph") # serve plotted graphs
app.mount("/static", StaticFiles(directory=static_dir), name="static") # serve static files

# Serve landing page
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

class Query(BaseModel):
    user_input: str

# handle chat requests
@app.post("/api/ask")
async def ask(query: Query):
    graph_url=os.path.join(graph_folder, f"graph_{uuid.uuid4().hex[:8]}.png")
    response = query_agent(query.user_input, graph_url)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        # ssl_keyfile=os.environ.get('KEY_FILE'),
        # ssl_certfile=os.environ.get('CERT_FILE'),
        # ssl_version=ssl.PROTOCOL_TLS_SERVER
    )