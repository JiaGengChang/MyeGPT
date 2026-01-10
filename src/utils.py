import re
import json

# present structured tool message in html
def format_step_tool(step:dict):
    # Tool result
    msg = step['tools']['messages'][0].text()
    if len(msg.strip()) > 0:
        if "<div class=image-container>" in msg:
            formatted_msg = f"🛠️ Tool result: {msg}"
        else:
            formatted_msg = f"🛠️ Tool result:<div class=\"scrollable lightaccent codeblock\">{msg}</div>"
    else:
        # python_repl_ast is called upon for plotting
        formatted_msg = f'🛠️ Tool result: {str(step)}'
    return formatted_msg

# present structured AI response or unstructured tool response in html
def format_step_agent(step:dict):
    msg = step['agent']['messages'][0].text()
    if len(msg.strip()) > 0: 
        # the AI answer
        formatted_msg = f"🤖 Agent: {msg}"
    else:
        # Tool call
        # that's why its an Ai message with no content
        # remove Ai message heading
        msg = '\n'.join(step['agent']['messages'][0].pretty_repr().split('\n')[1:])
        # Add HTML code block tags for the query part
        if "Tool Calls:\n" in msg:
            match = re.split(r"Args:\n", msg, maxsplit=1)
            if len(match) == 2:
                match_query = re.split(r"\ +Args:\s+query: ", msg, maxsplit=1)
                if len(match_query) == 2:
                    msg = f"{match_query[0]}Args: query:\n<div class=\"scrollable lightaccent codeblock\">{match_query[1]}</div>"
                else:
                    msg = f"{match[0]}Args:\n<div class=\"scrollable lightaccent codeblock\">{match[1]}</div>"
        formatted_msg = f"🤖 {msg}"
    return formatted_msg

def parse_step(step):
    if 'agent' in step:
        formatted_msg = format_step_agent(step)
    elif 'tools' in step:
        formatted_msg = format_step_tool(step)
    else:
        msg = json.dumps(step, indent=2, ensure_ascii=False, default=str)
        formatted_msg = f'⁉️ Unparsed message: {msg}'
    return formatted_msg