import os
import json
import subprocess
from typing import Any
from anthropic.types import ToolParam

TOOLS_SCHEME = [
    ToolParam(
        name="read_file",
        description="Read the contents of a given relative file path. Use this when you want to see what's inside a file. Do not use this with directory names.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["file_path"],
        },
    ),
    ToolParam(
        name="edit_file",
        description="Make edits to a text file. Replaces 'old_str' with 'new_str' in the given file. 'old_str' and 'new_str' MUST be different to each other. If the file specified with path does not exist, it will be created.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file"},
                "old_str": {
                    "type": "string",
                    "description": "Text to search for - must match exactly and must only have one match exactly",
                },
                "new_str": {
                    "type": "string",
                    "description": "Text to replace old_str with",
                },
            },
            "required": ["file_path", "old_str", "new_str"],
        },
    ),
    ToolParam(
        name="find_code_patterns",
        description="FIRST STEP FOR ANY CODE ANALYSIS. Finds specific functions/vars via regex.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "examples": ["def calculate_risk", "class User"],
                },
                "file_filter": {"type": "string", "examples": ["*.py", "src/*.ts"]},
            },
            "required": ["pattern", "file_filter"],
        },
    ),
    ToolParam(
        name="read_code_snippet",
        description="READ ONLY AFTER SEARCHING. Gets 10 lines around matches from find_code_patterns.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "line_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "From find_code_patterns results",
                },
            },
            "required": ["file_path", "line_numbers"],
        },
    ),
]


def create_new_file(file_path: str, content: str) -> tuple[str, Exception | None]:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        return "OK", None
    except Exception as e:
        return "", e


def read_file(file_path: str) -> tuple[str, Exception | None]:
    if not file_path:
        return "", ValueError("Missing file_path parameter")
    try:
        with open(file_path, "r") as file:
            return file.read(), None
    except Exception as e:
        return "", e


def edit_file(
    file_path: str, old_str: str, new_str: str
) -> tuple[str, Exception | None]:
    try:
        with open(file_path, "r") as file:
            content = file.read()

        if old_str not in content:
            return "", ValueError(f"'{old_str}' not found in file '{file_path}'")

        content = content.replace(old_str, new_str)

        with open(file_path, "w") as file:
            file.write(content)

        return "OK", None
    except Exception as e:
        return "", e


def list_files(path: str = ".") -> tuple[str, Exception | None]:
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


def find_code_patterns(pattern: str, file_filter: str) -> tuple[str, Exception | None]:
    try:
        cmd = [
            "git",
            "grep",
            "-n",
            "-I",
            "--color=never",
            "-e",
            pattern,
            "--",
            file_filter,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        lines = result.stdout.splitlines()[:5]  # Limit to 5 results
        if not lines:
            return "No matches found", None
        return "\n".join(lines), None
    except Exception as e:
        return f"Search failed: {str(e)}", None


def read_code_snippet(
    file_path: str, line_numbers: list[int]
) -> tuple[str, Exception | None]:
    if not os.path.exists(file_path):
        return f"File not found: {file_path}", None
    try:
        with open(file_path, "r") as f:
            content = f.readlines()
        out = []
        for ln in line_numbers:
            for i in range(max(ln - 3, 0), min(ln + 2, len(content))):
                line = content[i].rstrip()
                out.append(f"{i+1}: {line}")
                if len(out) >= 15:
                    out.append("...truncated...")
                    return "\n".join(out), None
        return "\n".join(out), None
    except Exception as e:
        return f"Read failed: {str(e)}", None


def tool_dispatcher(tool_name: str, tool_args: Any) -> tuple[str, Exception | None]:
    if tool_name == "read_file":
        return read_file(**tool_args)
    elif tool_name == "edit_file":
        return edit_file(**tool_args)
    elif tool_name == "list_files":
        return list_files(**tool_args)
    elif tool_name == "find_code_patterns":
        return find_code_patterns(**tool_args)
    elif tool_name == "read_code_snippet":
        return read_code_snippet(**tool_args)
    else:
        return "", ValueError(f"Unknown tool: {tool_name}")
