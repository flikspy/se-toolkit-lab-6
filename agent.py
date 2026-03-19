#!/usr/bin/env python3
"""
Agent CLI - Connects to an LLM and answers questions.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    JSON with 'answer' and 'tool_calls' fields to stdout.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def load_env() -> None:
    """Load environment variables from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if env_file.exists():
        load_dotenv(env_file)


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


def call_lllm(question: str, config: dict[str, str]) -> str:
    """Call the LLM API and return the answer."""
    url = f"{config['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
        "temperature": 0.7,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
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


def format_response(answer: str) -> dict:
    """Format the response as required JSON structure."""
    return {
        "answer": answer,
        "tool_calls": [],
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent CLI - Ask questions to an LLM")
    parser.add_argument("question", help="The question to ask the LLM")
    args = parser.parse_args()

    # Load environment configuration
    load_env()
    config = get_llm_config()

    # Call LLM and get answer
    answer = call_lllm(args.question, config)

    # Format and output response
    response = format_response(answer)
    print(json.dumps(response))


if __name__ == "__main__":
    main()
