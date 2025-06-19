import os
import uuid
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# src modules
from agent import query_agent

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

    user_input = query.user_input
    filename = f"graph_{uuid.uuid4().hex[:8]}.png"
    full_prompt = f"""
    PRE-AMBLE: If a graph is generated, call plt.savefig() to save the graph as '{filename}' in the folder '{graph_folder}' and do not mention anything about the graph being saved or generated. Do not plt.show() as the canvas is non-interactive.
    USER INPUT: {user_input}
    """

    response = query_agent(full_prompt)

    graph_path = os.path.join(graph_folder, filename)
    graph_url = None
    
    if os.path.exists(graph_path):
        graph_url = f"graph/{filename}"

    print(f"\n\nGRAPH URL : {graph_url}\n\n")
    return {
        "response": response,
        "graph_url": graph_url
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        timeout_keep_alive=60
    )