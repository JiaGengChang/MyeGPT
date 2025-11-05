import os
import json
from pprint import pformat
from fastapi import FastAPI
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import uuid
import matplotlib
import psycopg
matplotlib.use('Agg') # non-interactive backend
import logging

from tools import document_search_tool, convert_gene_tool, gene_metadata_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool, display_plot_tool, generate_graph_filepath_tool
from utils import format_text_message

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session
# removed db description
def create_system_message() -> str:
    db_uri = os.environ.get("COMMPASS_DB_URI")
    db = SQLDatabase.from_uri(db_uri)
    with open(f'{os.path.dirname(__file__)}/prompt.txt', 'r') as f:
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
    elif model_id.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model=model_id,
            temperature=0,
            max_tokens=5000,
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
        tools=[document_search_tool, convert_gene_tool, gene_metadata_tool, langchain_query_sql_tool, python_repl_tool, python_execute_sql_query_tool, generate_graph_filepath_tool, display_plot_tool],
        checkpointer=app.state.checkpointer,
    )
    system_message = create_system_message()
    try:
        init_response = await graph.ainvoke({"messages" : system_message}, config_init)
        # Store the init response for injection into HTML
        app.state.init_response = init_response["messages"][-1].content
    except Exception as e1:
        try:
            await handle_invalid_chat_history(app, e1)
            app.state.init_response = "Crash recovery succeeded."
        except Exception as e2:
            # likely input length exceeded
            app.state.init_response = f"Error during initialization: {e2}"

    
    # Open the gate for queries
    app.state.init_prompt_done.set()

def query_agent(user_input: str):
    global graph
    global config_ask
    user_message = HumanMessage(content=user_input)
    
    for step in graph.stream({"messages": [user_message]}, config_ask, stream_mode="updates"):
        print(step)
        pretty = json.dumps(step, indent=2, ensure_ascii=False, default=str)
        yield pretty
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

async def handle_invalid_chat_history(app: FastAPI, e: Exception):
        global graph
        global config_ask
        if "Found AIMessages with tool_calls that do not have a corresponding ToolMessage" in str(e):
            # get the list of most recent messages from the graph state with graph.getState(config)
            state = await graph.aget_state(config_ask)
            # modify the list of messages remove unanswered tool calls from AIMessages
            for step in range(len(state[0]["messages"]) - 1, -1, -1):
                msg = state[0]["messages"][step]
                # support both dict-like and object-like messages
                msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
                additional_kwargs = msg.get("additional_kwargs") if isinstance(msg, dict) else getattr(msg, "additional_kwargs", None)
                if msg_type == "ai" and isinstance(additional_kwargs, dict) and "tool_calls" in additional_kwargs:
                    logging.warning(f"Removing potential AIMessage without accompanying ToolMessage: {pformat(msg)}")
                    break

            # delete all checkpoints after offending message to attempt to reload
            auth_db_conn = psycopg.connect(os.environ.get("COMMPASS_AUTH_DSN"))
            with auth_db_conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM commpass_schema.checkpoints
                    WHERE thread_id = %s
                        AND (metadata->>'step') IS NOT NULL
                        AND (metadata->>'step')::int >= %s
                    """,
                    (app.state.username, step),
                )
                auth_db_conn.commit()
            
            state[0]["messages"] = state[0]["messages"][:step]
            await graph.aupdate_state(config_ask, state)

            # resume the graph
            await graph.ainvoke(None, config_ask)
        else:
            raise e
