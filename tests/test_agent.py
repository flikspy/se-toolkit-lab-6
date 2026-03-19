"""Regression tests for agent.py CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json_with_required_fields() -> None:
    """Test that agent.py outputs valid JSON with 'answer' and 'tool_calls' fields.

    This test runs agent.py as a subprocess with a simple question,
    parses the stdout JSON, and verifies the required fields are present.
    """
    # Get the project root directory (parent of tests/)
    project_root = Path(__file__).parent.parent

    # Check if .env.agent.secret exists, skip if not configured
    env_file = project_root / ".env.agent.secret"
    if not env_file.exists():
        # Create a minimal env file for testing if example exists
        example_file = project_root / ".env.agent.example"
        if example_file.exists():
            # Skip test if not configured - this is expected in CI
            return

    # Run agent.py with a simple question
    agent_path = project_root / "agent.py"
    result = subprocess.run(
        ["uv", "run", "--active", str(agent_path), "What is 2 + 2?"],
        capture_output=True,
        text=True,
        timeout=65,  # Slightly more than the 60s agent timeout
        cwd=str(project_root),
        env={**os.environ},
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        response = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON output: {e}\nStdout: {result.stdout}")

    # Verify 'answer' field exists and is non-empty
    assert "answer" in response, "Missing 'answer' field in response"
    assert isinstance(response["answer"], str), "'answer' must be a string"
    assert len(response["answer"]) > 0, "'answer' must not be empty"

    # Verify 'tool_calls' field exists and is an array
    assert "tool_calls" in response, "Missing 'tool_calls' field in response"
    assert isinstance(response["tool_calls"], list), "'tool_calls' must be an array"
