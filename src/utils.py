import re

# present structured tool message in html
def format_tool_message(message: dict) -> str:
    tool_name = message.get('name', 'Unknown Tool')
    tool_input = message.get('input', {})
    
    formatted = f"🛠️ Tool call: `{tool_name}`\n"
    
    if isinstance(tool_input, dict):
        for key, value in tool_input.items():
            formatted += f"  {key}: <div class='code'>{value}</div>"
    else:
        formatted += f"  input: <div class='code'>{tool_input}</div>"

    return formatted

# present structured AI response or unstructured tool response in html
def format_text_message(message) -> str:
    if isinstance(message, dict):
        content = message.get('text', '')
    else:
        content = str(message)
    
    # Detect if the content contains tool results (e.g., text within [ ])
    if re.search(r"\[\(.*?\)\]", content) or re.search(r"The top \d+ table\(s\) with best match:", content):
        # scrollable div to reduce clutter
        content = f'<div class="scrollable_tool_result">{content}</div>'
        formatted = f"🛠️ Tool result: {content}"
    else:
        formatted = f"💬 {content}"

    return formatted
