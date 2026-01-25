import os
from fastapi import FastAPI
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
import matplotlib
import psycopg
matplotlib.use('Agg') # non-interactive backend
import logging

# import user modules
from chat_agent_executor import create_react_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_experimental.tools import PythonAstREPLTool
from tools import ConvertGeneTool, CoxPHStatsLog2TPMExprTool, CoxRegressionBaseDataTool, DisplayPlotTool, DocumentSearchTool, GeneCopyNumberTool, GenerateGraphFilepathTool, MADLog2TPMExprTool, PythonSQLTool
from llm_utils import universal_chat_model
from utils import parse_step

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

async def send_init_prompt(app:FastAPI) -> None:
    # initializes LLM, stores response in app.state.init_response
    # then flags app.state.init_prompt_done event as done
    global graph
    global config_ask
    config_init = {"thread_id": app.state.username, "recursion_limit": 5} # init configuration
    config_ask = {"thread_id": app.state.username, "recursion_limit": 50} # ask configuration

    #  initialize the chat model
    llm = universal_chat_model(os.environ.get("MODEL_ID"))
    
    graph = create_react_agent(
        model=llm,
        tools = [ConvertGeneTool(),
                 PythonAstREPLTool(),
                 QuerySQLDatabaseTool(db=SQLDatabase.from_uri(os.environ.get("COMMPASS_DB_URI"))),
                 PythonSQLTool(),
                 DocumentSearchTool(),
                 GenerateGraphFilepathTool(),
                 DisplayPlotTool(),
                 GeneCopyNumberTool(),
                 CoxRegressionBaseDataTool(),
                 CoxPHStatsLog2TPMExprTool(),
                 MADLog2TPMExprTool()
                 ],
        # tools=[document_search_tool, 
        #        gene_level_copy_number_tool, 
        #        cox_regression_base_data_tool, 
        #        coxph_stats_log2tpm_expr_tool, 
        #        mad_log2tpm_expr_tool,
        #        langchain_query_sql_tool, 
        #        python_repl_tool, 
        #        python_execute_sql_query_tool,
        #        display_plot_tool, 
        #        generate_graph_filepath_tool
        #        ],
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
            app.state.init_response = f"Crash recovery unsuccessful. Consider erasing memory. Error: {e2}"
    finally:
        # release /api/init from waiting
        app.state.init_prompt_done.set()
    
    return

def query_agent(user_input: str):
    global graph
    global config_ask
    user_message = HumanMessage(content=user_input)
    
    for step in graph.stream({"messages": [user_message]}, config_ask, stream_mode="updates"):
        # for python tty
        print(step)
        # for frontend
        # the following parsing is based on GPT-5-Mini. 
        # It may not work for other LLMS.
        yield parse_step(step)

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
                logging.warning(f"Removing potential AIMessage without accompanying ToolMessage: {str(msg)}")
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

__all__ = [
    "send_init_prompt",
    "query_agent"
]