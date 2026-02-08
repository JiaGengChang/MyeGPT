import os
from fastapi import FastAPI
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
import matplotlib
import psycopg
matplotlib.use('Agg') # non-interactive backend
import logging

# import user modules
from executor import create_react_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_experimental.tools import PythonAstREPLTool
from tools import ConvertGeneTool, CoxPHStatsLog2TPMExprTool, CoxRegressionBaseDataTool, DisplayPlotTool, DocumentSearchTool, GeneCopyNumberTool, GeneMetadataTool, GenerateGraphFilepathTool, MADLog2TPMExprTool, RetrieveGeneListTool, PythonSQLTool
from llm_utils import universal_chat_model
from utils import parse_step
from variables import COMMPASS_DB_URI, COMMPASS_AUTH_DSN, MODEL_ID

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session
# removed db description
def create_system_message() -> str:
    db = SQLDatabase.from_uri(COMMPASS_DB_URI)
    with open(f'{os.path.dirname(__file__)}/prompt.txt', 'r') as f:
        latent_system_message = f.read()
    system_message = latent_system_message.format(
        dialect=db.dialect,
        commpass_db_uri=COMMPASS_DB_URI
    )
    return [HumanMessage(content='Hello, MyeGPT!'),
            SystemMessage(content=system_message)]

async def send_init_prompt(app:FastAPI) -> None:
    # initializes LLM, stores response in app.state.init_response
    # then flags app.state.init_prompt_done event as done
    global graph
    global config_ask
    config_init = {"configurable":{"thread_id": app.state.username, "recursion_limit": 5}} # init configuration
    config_ask = {"configurable":{"thread_id": app.state.username, "recursion_limit": 50}} # ask configuration

    #  initialize the chat model
    llm = universal_chat_model(MODEL_ID)

    commpass_db = SQLDatabase.from_uri(COMMPASS_DB_URI)

    graph = create_react_agent(
        model=llm,
        tools = [ConvertGeneTool(),
                 GeneMetadataTool(),
                 PythonAstREPLTool(),
                 QuerySQLDatabaseTool(db=commpass_db),
                 PythonSQLTool(),
                 DocumentSearchTool(),
                 GenerateGraphFilepathTool(),
                 DisplayPlotTool(),
                 GeneCopyNumberTool(),
                 CoxRegressionBaseDataTool(),
                 CoxPHStatsLog2TPMExprTool(),
                 MADLog2TPMExprTool(),
                 RetrieveGeneListTool()
                 ],
        checkpointer=app.state.checkpointer,
    )

    system_message = create_system_message()

    try:
        init_response = await graph.ainvoke({"messages" : system_message}, config_init)
        # Store the init response for injection into HTML
        app.state.init_response = init_response["messages"][-1].content
        # dictionary with token usage info
        # for updating in parse_step
        # {'input_tokens': 16172, 'output_tokens': 289, 'total_tokens': 16461, 'input_token_details': {'audio': 0, 'cache_read': 13952}, 'output_token_details': {'audio': 0, 'reasoning': 128}}
        app.state.usage_metadata = init_response["messages"][-1].usage_metadata
    except Exception as e1:
        try:
            await handle_invalid_chat_history(app, e1)
            app.state.init_response = "Crash recovery succeeded."            
        except Exception as e2:
            # likely input length exceeded
            app.state.init_response = f"Initialization error: {e2}"
    finally:
        # release /api/init from waiting
        app.state.init_prompt_done.set()
    
    return

def query_agent(app: FastAPI, user_input: str):
    global graph
    global config_ask
    user_message = HumanMessage(content=user_input)
    
    try:
        for step in graph.stream({"messages": [user_message]}, config_ask, stream_mode="updates"):
            # for python tty
            print(step)
            # for frontend
            # the following parsing is based on GPT-5-Mini. 
            # It may not work for other LLMS.
            yield parse_step(step, app.state.usage_metadata)
    except Exception as e:
        # handle openai.BadRequestError: Error code: 400 - {'error': {'message': 'Input tokens exceed the configured limit of 272000 tokens. Your messages resulted in 287850 tokens. Please reduce the length of the messages.', 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}}
        yield f"⁉️ Unexpected message: {str(e)}"

async def handle_invalid_chat_history(app: FastAPI, e: Exception):
    global graph
    global config_ask
    if "Found AIMessages with tool_calls that do not have a corresponding ToolMessage" in str(e) or "bypass" == str(e):

        # get the list of most recent messages from the graph state with graph.getState(config)
        state = await graph.aget_state(config_ask)
        
        if "messages" in state[0]:
            response_code = 1 # 1 = no changes, 2 = deletion made
            # modify the list of messages remove unanswered tool calls from AIMessages
            for step in range(len(state[0]["messages"]) - 1, -1, -1):
                msg = state[0]["messages"][step]
                # support both dict-like and object-like messages
                msg_type = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
                additional_kwargs = msg.get("additional_kwargs") if isinstance(msg, dict) else getattr(msg, "additional_kwargs", None)
                if msg_type == "ai" and isinstance(additional_kwargs, dict) and "tool_calls" in additional_kwargs:
                    logging.warning(f"Removing potential AIMessage without accompanying ToolMessage: {str(msg)}")
                    response_code = 2
                    break

            # delete all checkpoints after offending message to attempt to reload
            auth_db_conn = psycopg.connect(COMMPASS_AUTH_DSN)
            with auth_db_conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM checkpoints.checkpoints
                    WHERE thread_id = %s
                        AND (metadata->>'step') IS NOT NULL
                        AND (metadata->>'step')::int >= %s
                    """,
                    (app.state.username, step),
                )
                auth_db_conn.commit()
            
            state[0]["messages"] = state[0]["messages"][:step]
            await graph.aupdate_state(config_ask, state, as_node='tools')
            await graph.ainvoke({"messages": create_system_message()}, config_ask)  # empty messages to trigger reload
            return response_code
        else:
            # conversation history is empty
            return 0

    else:
        raise e

__all__ = [
    "handle_invalid_chat_history",
    "send_init_prompt",
    "query_agent"
]