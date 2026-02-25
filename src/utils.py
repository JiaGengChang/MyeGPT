import re
import json

# present structured tool message in html
def format_step_tool(step:dict):
    # Tool result
    msg = step['tools']['messages'][0].text
    if len(msg.strip()) > 0:
        if "<div class=image-container>" in msg:
            formatted_msg = f"🛠️ Tool result: {msg}"
        else:
            formatted_msg = f"🛠️ Tool result:<div class=\"scrollable lightaccent codeblock\">{msg}</div>"
    else:
        # python_repl_ast is called upon for plotting
        formatted_msg = f'🛠️ Tool result: {str(step)}'
    return formatted_msg

def _recursive_update(target, source):
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            _recursive_update(target[k], v)
        elif k in target:
            target[k] += v
        else:
            target[k] = v
    
# present structured AI response or unstructured tool response in html
def format_step_agent(step:dict, session_state:dict):
    msg = step['agent']['messages'][0].text
    metadata = step['agent']['messages'][0].usage_metadata
    _recursive_update(session_state, metadata)
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

def parse_step(step:dict, session_state: dict):
    if 'agent' in step:
        formatted_msg = format_step_agent(step, session_state)
    elif 'tools' in step:
        formatted_msg = format_step_tool(step)
    else:
        msg = json.dumps(step, indent=2, ensure_ascii=False, default=str)
        formatted_msg = f'⁉️ Unparsed message: {msg}'
    return formatted_msg


# Order the samples using the oncoplot algorithm
def oncoplot_ordering(data,extra_covariates=[],prioritize_covariates=False):
    import pandas as pd
    # Define a recursive function to order the data
    def recursive_ordering(data, depth=0):
        if depth >= data.shape[1]:
            return data.index.tolist()
        
        # Order columns by column-wise sum
        primary_col = ordered_columns[depth]
                
        # The remaining are IGH partner columns
        # Divide observations into groups based on the primary column
        
        ordered_indices = []
        
        for value in sorted(data[primary_col].unique())[::-1]:
            # subset to observations with the same value
            group_v = data[data[primary_col] == value]
            # Recursively order within each group
            ordered_indices_v = recursive_ordering(group_v, depth + 1)
            # Combine the ordered indices
            ordered_indices.extend(ordered_indices_v)
        
        return ordered_indices
    
    # Start the recursive ordering
    # Order by number of carriers
    # ordered_columns = (data==1).sum(axis=0).sort_values(ascending=False).index
    heatmap_data = data.drop(columns=extra_covariates)
    ordered_heatmap_columns = (heatmap_data==1).sum(axis=0).sort_values(ascending=False).index
    
    # Order additional columns appear last
    if prioritize_covariates:    
        ordered_columns = pd.Index(extra_covariates).append(ordered_heatmap_columns)
    else:
        ordered_columns = ordered_heatmap_columns.append(pd.Index(extra_covariates))
    
    ordered_indices = recursive_ordering(data.loc[:, ordered_columns])
    return data.loc[ordered_indices, ordered_columns]
