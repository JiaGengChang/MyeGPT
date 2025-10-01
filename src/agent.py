import os
from fastapi import FastAPI
from langchain_community.utilities import SQLDatabase
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import uuid
import matplotlib
matplotlib.use('Agg') # non-interactive backend

from tools import document_search_tool, convert_gene_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool
from utils import format_text_message, format_tool_message

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session
# removed db description
def create_system_message() -> str:
    db_uri = os.environ.get("COMMPASS_DB_URI")
    db = SQLDatabase.from_uri(db_uri)
    with open('prompt.txt', 'r') as f:
        latent_system_message = f.read()
    system_message = latent_system_message.format(
        dialect=db.dialect,
        commpass_db_uri=db_uri
    )
    return [HumanMessage(content='Hello, MyeGPT!'),
            SystemMessage(content=system_message)]

async def send_init_prompt(app:FastAPI):
    global graph
    global config_ask
    config_init = {"configurable": {"thread_id": app.state.username, "recursion_limit": 5}} # init configuration
    config_ask = {"configurable": {"thread_id": app.state.username, "recursion_limit": 50}} # ask configuration

    #  initialize the chat model
    model_id = os.environ.get("MODEL_ID")
    if not model_id:
        raise ValueError("MODEL_ID environment variable is not set")
    elif model_id.startswith("gpt-"):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=model_id,
            temperature=0.,
            max_tokens=5000, # 4096 for gpt-3.5-turbo, 10_000 for the rest
        )
    else:
        from langchain_aws import ChatBedrockConverse
        llm = ChatBedrockConverse(
            model_id=os.environ.get("MODEL_ID"),
            temperature=0.,
            max_tokens=5000, # 4096 for claude-3-haiku, 10_000 for the rest
        )
    graph = create_react_agent(
        model=llm,
        tools=[document_search_tool, convert_gene_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool],
        checkpointer=app.state.checkpointer,
    )
    system_message = create_system_message()
    init_response = await graph.ainvoke({"messages" :system_message}, config_init)

    # Store the init response for injection into HTML
    app.state.init_response = init_response["messages"][-1].content
    
    # Open the gate for queries
    app.state.init_prompt_done.set()

def query_agent(user_input: str):
    global graph
    global config_ask
    graph_png_filename = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
    preamble = SystemMessage(f"""
                             If a graph is created, save it as {graph_png_filename} and display with `<img src={graph_png_filename} width=100% height=auto>`.
                             """)
    user_message = HumanMessage(content=user_input)
    
    for step in graph.stream({"messages": [preamble, user_message]}, config_ask, stream_mode="updates"):
        print(step)
        chunks = None
        if "agent" in step:
            chunks = step["agent"]["messages"][-1].content
            if isinstance(chunks, list):
                for chunk in chunks:
                        if chunk["type"]=="text":
                            chunk = format_text_message(chunk)
                            yield str(chunk)
            elif isinstance(chunks, dict):
                if chunk["type"]=="text":
                    chunk = format_text_message(chunk)
                    yield str(chunk)
            else:
                if chunks!="":
                    yield format_text_message(chunks)