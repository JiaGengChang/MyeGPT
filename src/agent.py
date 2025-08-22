import os
from fastapi import FastAPI
from langchain_community.utilities import SQLDatabase
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import uuid
import matplotlib
matplotlib.use('Agg') # non-interactive backend

from vectorstore import connect_store
from tools import document_search_tool, convert_gene_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool

# create a QUERY SQL tool
db_uri = os.environ.get("COMMPASS_DB_URI")
db = SQLDatabase.from_uri(db_uri)

# initialize the chat model
llm = ChatBedrockConverse(
    model_id=os.environ.get("MODEL_ID"),
    temperature=0.,
)

# Create runnable graph
graph = create_react_agent(
    model=llm,
    tools=[document_search_tool, convert_gene_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool],
    checkpointer=InMemorySaver(),
    store=connect_store(),
)

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session
# removed db description
def create_system_message() -> str:
    with open('prompt.txt', 'r') as f:
        latent_system_message = f.read()
    system_message = latent_system_message.format(
        dialect=db.dialect,
        commpass_db_uri=db_uri
    )
    return system_message

system_message = None
config = {"configurable": {"thread_id": "thread-001"}, "recursion_limit": 50}

async def send_init_prompt(app:FastAPI):
    global system_message
    global graph
    global config
    system_message = create_system_message()
    init_response = await graph.ainvoke({"messages" :[system_message]}, config)

    # Store the init response for injection into HTML
    app.state.init_response = init_response["messages"][-1].content
    
    # Open the gate for queries
    app.state.init_prompt_done.set()

def query_agent(user_input: str):
    global graph
    global config
    graph_png_filename = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
    preamble = SystemMessage(f"""
                             If a graph is created, save it as {graph_png_filename} and display with `<img src={graph_png_filename} width=100% height=auto>`.
                             """)
    user_message = HumanMessage(content=user_input)
    
    for step in graph.stream({"messages": [preamble, user_message]}, config, stream_mode="values"):
        if step["messages"]:
            step["messages"][-1].pretty_print()
            if isinstance(step["messages"][-1], AIMessage):
                chunk = step["messages"][-1].content
                if isinstance(chunk, list):
                    chunk = chunk[0]
                if isinstance(chunk, dict) and "text" in chunk:
                    chunk = chunk["text"][:-1]
                if isinstance(chunk, str):
                    yield chunk