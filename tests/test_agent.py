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


def _is_rate_limited(result: subprocess.CompletedProcess) -> bool:
    """Check if the result indicates API rate limiting or spending limit."""
    return (
        "429" in result.stderr
        or "402" in result.stderr
        or "rate limit" in result.stderr.lower()
        or "spending limit" in result.stderr.lower()
    )


def test_agent_outputs_valid_json_with_required_fields() -> None:
    """Test that agent.py outputs valid JSON with 'answer', 'source', and 'tool_calls' fields."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        example_file = project_root / ".env.agent.example"
        if example_file.exists():
            return

    result = run_agent("What is 2 + 2?")

    # Skip if API rate limited
    if _is_rate_limited(result):
        return

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    assert "answer" in response, "Missing 'answer' field"
    assert isinstance(response["answer"], str), "'answer' must be a string"
    assert len(response["answer"]) > 0, "'answer' must not be empty"

    assert "source" in response, "Missing 'source' field"
    assert isinstance(response["source"], str), "'source' must be a string"

    assert "tool_calls" in response, "Missing 'tool_calls' field"
    assert isinstance(response["tool_calls"], list), "'tool_calls' must be an array"


def test_merge_conflict_question_uses_read_file() -> None:
    """Test that merge conflict question triggers read_file tool."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        return

    result = run_agent("How do you resolve a merge conflict?")

    # Skip if API rate limited
    if _is_rate_limited(result):
        return

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "read_file" in tool_names, "Expected 'read_file' in tool_calls"

    source = response.get("source", "")
    assert source.startswith("wiki/"), (
        f"Source should start with 'wiki/', got: {source}"
    )


def test_wiki_files_question_uses_list_files() -> None:
    """Test that wiki files question triggers list_files tool."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        return

    result = run_agent("What files are in the wiki?")

    # Skip if API rate limited
    if _is_rate_limited(result):
        return

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    assert len(response["tool_calls"]) > 0, "Expected non-empty tool_calls"

    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "list_files" in tool_names, "Expected 'list_files' in tool_calls"


def test_framework_question_uses_read_file() -> None:
    """Test that framework question triggers read_file tool for source code."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"

    if not env_file.exists():
        return

    result = run_agent("What Python web framework does the backend use?")

    # Skip if API rate limited
    if _is_rate_limited(result):
        return

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "read_file" in tool_names, "Expected 'read_file' in tool_calls"

    answer = response.get("answer", "").lower()
    frameworks = ["fastapi", "flask", "django", "starlette", "pyramid"]
    assert any(fw in answer for fw in frameworks), (
        f"Answer should mention a web framework, got: {response.get('answer', '')}"
    )


def test_data_question_uses_query_api() -> None:
    """Test that data question triggers query_api tool."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.agent.secret"
    docker_env_file = project_root / ".env.docker.secret"

    if not env_file.exists() or not docker_env_file.exists():
        return

    result = run_agent("How many items are in the database?")

    # Skip if backend is not running
    if (
        "Cannot connect to API" in result.stderr
        or "Cannot connect to API" in result.stdout
    ):
        return

    # Skip if API rate limited
    if _is_rate_limited(result):
        return

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    response = parse_response(result.stdout)

    tool_names = [tc.get("tool") for tc in response["tool_calls"]]
    assert "query_api" in tool_names, "Expected 'query_api' in tool_calls"

    api_calls = [tc for tc in response["tool_calls"] if tc.get("tool") == "query_api"]
    items_called = any(
        "/items" in tc.get("args", {}).get("path", "") for tc in api_calls
    )
    assert items_called, "Expected query_api to call /items/ endpoint"
