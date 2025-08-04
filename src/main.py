import os
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
result_folder = os.path.join(app_dir, 'result')
os.makedirs(result_folder, exist_ok=True)

app.mount("/result", StaticFiles(directory=result_folder), name="result") # serve csv files
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
    response = query_agent(query.user_input)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
    )