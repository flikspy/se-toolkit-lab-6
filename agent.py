#!/usr/bin/env python3
"""
Agent CLI - Connects to an LLM with tools and answers questions.

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    JSON with 'answer', 'source', and 'tool_calls' fields to stdout.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# System prompt for the system agent
SYSTEM_PROMPT = """You are a documentation and system agent that answers questions about a software engineering project.

You have access to three tools:
1. list_files - List files in a directory (use for discovering wiki files)
2. read_file - Read the contents of a file (use for wiki docs or source code)
3. query_api - Call the backend LMS API (use for live data: items, scores, analytics)

When answering questions:
- For wiki/documentation questions: use list_files to discover files, then read_file to read content
- For source code questions: use read_file to examine the code (e.g., backend/app/main.py for framework info)
- For data questions (how many items, what's the score, completion rate): use query_api
- For system facts (framework, ports, status codes): check wiki first, then source code

Always provide a source reference when possible:
- Wiki: wiki/filename.md#section-anchor (use lowercase, hyphens for spaces)
- Source code: backend/app/filename.py or the actual file path
- API data: API endpoint path (e.g., "GET /items/" or "GET /analytics/completion-rate")

Rules:
- Use the right tool for the question type
- Maximum 10 tool calls per question
- If you cannot find the answer, say so honestly
"""


def load_env() -> None:
    """Load environment variables from .env.agent.secret and .env.docker.secret."""
    # Load LLM config
    env_file = Path(__file__).parent / ".env.agent.secret"
    if env_file.exists():
        load_dotenv(env_file, override=False)

    # Load LMS API config
    docker_env_file = Path(__file__).parent / ".env.docker.secret"
    if docker_env_file.exists():
        load_dotenv(docker_env_file, override=False)


def get_llm_config() -> dict[str, str]:
    """Get LLM configuration from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL", "qwen3-coder-plus")

    if not api_key:
        print("Error: LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set", file=sys.stderr)
        sys.exit(1)

    return {
        "api_key": api_key,
        "api_base": api_base.rstrip("/"),
        "model": model,
    }


def get_api_config() -> dict[str, str]:
    """Get backend API configuration from environment variables."""
    api_key = os.getenv("LMS_API_KEY")
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

    return {
        "api_key": api_key or "",
        "base_url": base_url.rstrip("/"),
    }


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def validate_path(relative_path: str, project_root: Path) -> Path:
    """Validate and resolve a relative path within project root.

    Security: Prevents path traversal attacks by:
    1. Rejecting paths containing '..'
    2. Rejecting absolute paths
    3. Verifying resolved path is within project root
    """
    # Reject path traversal
    if ".." in relative_path:
        raise ValueError("Path traversal not allowed")

    # Reject absolute paths
    if relative_path.startswith("/"):
        raise ValueError("Absolute paths not allowed")

    # Resolve to absolute path
    full_path = (project_root / relative_path).resolve()

    # Verify within project root
    if not str(full_path).startswith(str(project_root.resolve())):
        raise ValueError("Path outside project root not allowed")

    return full_path


def read_file(path: str) -> str:
    """Read the contents of a file from the project.

    Args:
        path: Relative path from project root (e.g., 'wiki/git-workflow.md')

    Returns:
        File contents as string, or error message if file doesn't exist
    """
    try:
        project_root = get_project_root()
        full_path = validate_path(path, project_root)

        if not full_path.exists():
            return f"Error: File not found: {path}"

        if not full_path.is_file():
            return f"Error: Not a file: {path}"

        return full_path.read_text()
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories in a directory.

    Args:
        path: Relative directory path from project root (e.g., 'wiki')

    Returns:
        Newline-separated listing of entries, or error message
    """
    try:
        project_root = get_project_root()
        full_path = validate_path(path, project_root)

        if not full_path.exists():
            return f"Error: Directory not found: {path}"

        if not full_path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = sorted([entry.name for entry in full_path.iterdir()])
        return "\n".join(entries)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str | None = None) -> str:
    """Call the backend LMS API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (e.g., '/items/', '/analytics/scores')
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and response body
    """
    api_config = get_api_config()
    base_url = api_config["base_url"]
    api_key = api_config["api_key"]

    url = f"{base_url}{path}"
    headers = {
        "Content-Type": "application/json",
    }

    # Add authentication header if API key is available
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                data = json.loads(body) if body else {}
                response = client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                data = json.loads(body) if body else {}
                response = client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return f"Error: Unsupported HTTP method: {method}"

            result = {
                "status_code": response.status_code,
                "body": response.text,
            }
            return json.dumps(result)
    except httpx.TimeoutException:
        return f"Error: API request timed out for {method} {path}"
    except httpx.ConnectError as e:
        return f"Error: Cannot connect to API at {base_url}: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {e}"
    except Exception as e:
        return f"Error: API request failed: {e}"


# Tool schemas for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project (wiki docs or source code)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/app/main.py')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a directory (use for discovering wiki files)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend LMS API to fetch live data (items, scores, analytics) or system information",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/scores', '/analytics/completion-rate')",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool function with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        arguments: Dictionary of arguments for the tool

    Returns:
        Result of the tool execution as a string
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {tool_name}"

    func = TOOL_FUNCTIONS[tool_name]
    try:
        return func(**arguments)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def call_llm(
    messages: list[dict[str, str]],
    config: dict[str, str],
    tools: list[dict] | None = None,
) -> dict:
    """Call the LLM API and return the response.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        config: LLM configuration dictionary
        tools: Optional list of tool schemas for function calling

    Returns:
        Dictionary with 'content' and 'tool_calls' keys
    """
    url = f"{config['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.7,
    }

    if tools:
        payload["tools"] = tools

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]

            # Extract tool calls if present
            tool_calls = []
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    if tc.get("type") == "function":
                        tool_calls.append(
                            {
                                "id": tc.get("id"),
                                "name": tc["function"]["name"],
                                "arguments": json.loads(tc["function"]["arguments"]),
                            }
                        )

            return {
                "content": message.get("content") or "",
                "tool_calls": tool_calls,
            }
    except httpx.TimeoutException:
        print("Error: LLM API request timed out (>60s)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(
            f"Error: LLM API returned error {e.response.status_code}", file=sys.stderr
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to call LLM API: {e}", file=sys.stderr)
        sys.exit(1)


def extract_source_from_answer(answer: str) -> str:
    """Extract source reference from the answer text.

    Looks for patterns like wiki/filename.md#section-anchor or backend/app/*.py in the answer.
    """
    import re

    # Look for wiki file references with anchors
    pattern = r"wiki/[\w-]+\.md#[\w-]+"
    match = re.search(pattern, answer)
    if match:
        return match.group(0)

    # Look for wiki file references without anchors
    pattern = r"wiki/[\w-]+\.md"
    match = re.search(pattern, answer)
    if match:
        return match.group(0)

    # Look for backend source file references
    pattern = r"backend/app/[\w/.]+\.py"
    match = re.search(pattern, answer)
    if match:
        return match.group(0)

    # Look for API endpoint references
    pattern = r"(GET|POST|PUT|DELETE)\s+/\S+"
    match = re.search(pattern, answer, re.IGNORECASE)
    if match:
        return match.group(0)

    return ""


def run_agentic_loop(question: str, config: dict[str, str]) -> dict:
    """Run the agentic loop to answer a question.

    Args:
        question: The user's question
        config: LLM configuration dictionary

    Returns:
        Dictionary with 'answer', 'source', and 'tool_calls' keys
    """
    # Initialize messages with system prompt and user question
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Track all tool calls for output
    all_tool_calls = []

    # Run agentic loop
    for iteration in range(MAX_TOOL_CALLS):
        # Call LLM with tool schemas
        response = call_llm(messages, config, tools=TOOL_SCHEMAS)

        # Check if LLM wants to call tools
        if response["tool_calls"]:
            # Execute each tool call
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["name"]
                arguments = tool_call["arguments"]

                # Execute the tool
                result = execute_tool(tool_name, arguments)

                # Record the tool call for output
                all_tool_calls.append(
                    {
                        "tool": tool_name,
                        "args": arguments,
                        "result": result,
                    }
                )

                # Append tool result as new message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    }
                )

            # Continue loop to get next LLM response
        else:
            # LLM provided final answer
            answer = response["content"]
            break
    else:
        # Hit maximum tool calls without final answer
        answer = "I reached the maximum number of tool calls (10) without finding a complete answer."

    # Extract source from answer
    source = extract_source_from_answer(answer)

    return {
        "answer": answer,
        "source": source,
        "tool_calls": all_tool_calls,
    }


def format_response(answer: str, source: str, tool_calls: list) -> dict:
    """Format the response as required JSON structure."""
    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls,
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent CLI - Ask questions to an LLM with tools"
    )
    parser.add_argument("question", help="The question to ask the LLM")
    args = parser.parse_args()

    # Load environment configuration
    load_env()
    config = get_llm_config()

    # Run agentic loop and get response
    result = run_agentic_loop(args.question, config)

    # Format and output response
    response = format_response(**result)
    print(json.dumps(response))


if __name__ == "__main__":
    main()
