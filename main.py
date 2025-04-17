import anthropic
import os
from dotenv import load_dotenv, find_dotenv
import requests
import json

tools = [
        {"name": "read_file",
         "description": "Read the contents of a given relative file path. Use this when you want to see what's inside a file. Do not use this with directory names.",
         "input_schema": {
             "type": "object",
             "properties": {
                 "file_path": {"type": "string", "description": "Path to the file"}
             },
            "required": ["file_path"]
         }},
         {
         "name": "edit_file",
         "description": "Make edits to a text file. Replaces 'old_str' with 'new_str' in the given file. 'old_str' and 'new_str' MUST be different to each other. If the file specified with path does not exist, it will be created.",
         "input_schema": {
             "type": "object",
             "properties": {
                 "file_path": {"type": "string", "description": "Path to the file"},
                 "old_str": {"type": "string", "description": "Text to search for - must match exactly and must only have one match exactly"},
                 "new_str": {"type": "string", "description": "Text to replace old_str with"}
             },
            "required": ["file_path", "old_str", "new_str"]
         }},
         {
         "name": "list_files",
         "description": "List files and directories at a given path. If no path is provided, list files in the current directory",
         "input_schema": {
             "type": "object",
             "properties": {
                 "path": {"type": "string", "description": "Optional relative path to list files from. Defaults to current directory if not provided."}
             },
            "required": ["path"]
         }}
    ]

def create_new_file(file_path, content):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        return "OK", None
    except Exception as e:
        return "", e

def read_file(file_path):
    if not file_path:
        return "", ValueError("Missing file_path parameter")
    try:
        with open(file_path, "r") as file:
            return file.read(), None
    except Exception as e:
        return "", e


def edit_file(file_path, old_str, new_str):
    with open(file_path, 'r') as file:
        content = file.read()

    if old_str not in content:
        raise ValueError(f"'{old_str}' not found in {file_path}")

    content = content.replace(old_str, new_str)

    with open(file_path, 'w') as file:
        file.write(content)

def list_files(path="."):
    files = []
    try:
        for root, dirs, filenames in os.walk(path):
            rel_root = os.path.relpath(root, path)
            if rel_root != ".":
                files.append(rel_root + "/")
            for file in filenames:
                rel_file = os.path.join(rel_root, file) if rel_root != "." else file
                files.append(rel_file)
        return json.dumps(files), None
    except Exception as e:
        return "", e

def tool_dispatcher(tool_name, tool_args):
    if tool_name == "read_file":
        return read_file(**tool_args)
    elif tool_name == "edit_file":
        return edit_file(**tool_args)
    elif tool_name == "list_files":
        return list_files(**tool_args)
    else:
        return "", f"Unknown tool: {tool_name}"

def chat_with_claude():
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    
    
    conversation = []

    print("Chat with Claude (Type Ctrl+C to exit)")

    try:
        while True:
            get_user_message = input("You: ")
            conversation.append({"role": "user", "content": get_user_message})

            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1024,
                messages=conversation,
                tools=tools,
                tool_choice={"type": "auto"},
            )
            tool_calls = [c for c in response.content if getattr(c, "type", None) == "tool_use"]

            if not tool_calls:
                print("Claude: ", response.content[0].text)
                conversation.append({"role": "assistant", "content": response.content[0].text})
                break

            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_args = tool_call.input
                result, error = tool_dispatcher(tool_name, tool_args)
                if error:
                    tool_response = f"Error: {error}"
                else:
                    tool_response = result

                conversation.append({"role": "tool", "content": tool_response, "tool_use_id": tool_call.id})


    except KeyboardInterrupt:
        print("\nExiting chat...")

def claude_suggest_fix(issue):
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )

    prompt = f"""
    You are a helpful assistant. I will provide you with an issue from a GitHub repository, and I want you to suggest a fix for it.

    Name of issue: {issue['title']}
    Description of issue: {issue['body']}

    Suggest a fix:
    """

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=512,
        messages = [
            {"role": "user", "content": prompt}
        ],
        tools=tools,
        tool_choice={"type": "auto"},
    )

    return response.content[0].text

def get_github_issues():
    headers = {
        'Authorization': f'Token {os.environ.get("GITHUB_API_KEY")}',
        'Accept': 'application/vnd.github.v3+json'
    }

    username = "hermansildnes"
    repo_name = "math-cli-tool"
    url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    params = {
        "state": "open",
        "per_page": 100,
        "page": 1
    }
    issues = []

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        issues.extend([issue for issue in data if "pull_request" not in issue])
        if "next" not in response.links:
            break

        params["page"] += 1
    return issues

def main():
    load_dotenv(find_dotenv())


    chat_with_claude()

    # issues = get_github_issues()
    # if not issues:
    #     print("No open issues found.")
    #     return
    
    # for issue in issues:
    #     print(f"Issue #{issue['number']}: {issue['title']}")
    #     fix = claude_suggest_fix(issue)
    #     print(f"Suggested fix: {fix}\n")






if __name__ == "__main__":
    main()