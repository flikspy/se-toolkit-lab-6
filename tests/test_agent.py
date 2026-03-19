"""Regression tests for agent.py CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> subprocess.CompletedProcess:
    """Run agent.py with a question and return the result."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    return subprocess.run(
        ["uv", "run", "--active", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=120,  # Give more time for agentic loop
        cwd=str(project_root),
        env={**os.environ},
    )


def parse_response(stdout: str) -> dict:
    """Parse agent response as JSON."""
    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON output: {e}\nStdout: {stdout}")


def test_agent_outputs_valid_json_with_required_fields() -> None:
    """Test that agent.py outputs valid JSON with 'answer', 'source', and 'tool_calls' fields.

    This test runs agent.py as a subprocess with a simple question,
    parses the stdout JSON, and verifies the required fields are present.
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        example_file = project_root / ".env.agent.example"
        if example_file.exists():
            return

    result = run_agent("What is 2 + 2?")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    assert "answer" in response, "Missing 'answer' field in response"
    assert isinstance(response["answer"], str), "'answer' must be a string"
    assert len(response["answer"]) > 0, "'answer' must not be empty"

    assert "source" in response, "Missing 'source' field in response"
    assert isinstance(response["source"], str), "'source' must be a string"

    assert "tool_calls" in response, "Missing 'tool_calls' field in response"
    assert isinstance(response["tool_calls"], list), "'tool_calls' must be an array"


def test_merge_conflict_question_uses_read_file() -> None:
    """Test that merge conflict question triggers read_file tool.

    Question: "How do you resolve a merge conflict?"
    Expected:
        - read_file in tool_calls
        - wiki/git-vscode.md or wiki/git.md in source
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        example_file = project_root / ".env.agent.example"
        if example_file.exists():
            return

    result = run_agent("How do you resolve a merge conflict?")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    # Check tool_calls contains read_file
    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "read_file" in tool_names, "Expected 'read_file' in tool_calls"

    # Check source contains wiki reference
    source = response.get("source", "")
    assert source.startswith("wiki/"), (
        f"Source should start with 'wiki/', got: {source}"
    )
    assert source.endswith(".md") or "#" in source, (
        f"Source should be a wiki file reference, got: {source}"
    )


def test_wiki_files_question_uses_list_files() -> None:
    """Test that wiki files question triggers list_files tool.

    Question: "What files are in the wiki?"
    Expected:
        - list_files in tool_calls
        - Non-empty tool_calls array
    """
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        example_file = project_root / ".env.agent.example"
        if example_file.exists():
            return

    result = run_agent("What files are in the wiki?")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    # Check tool_calls is non-empty
    assert len(response["tool_calls"]) > 0, "Expected non-empty tool_calls"

    # Check tool_calls contains list_files
    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "list_files" in tool_names, "Expected 'list_files' in tool_calls"

    # Check answer is non-empty
    assert len(response["answer"]) > 0, "'answer' must not be empty"
