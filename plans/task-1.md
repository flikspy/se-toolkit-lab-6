# Task 1: Call an LLM from Code - Implementation Plan

## Overview

Build a Python CLI (`agent.py`) that connects to an LLM API and returns structured JSON responses. This is the foundation for the agentic system.

## LLM Provider Choice

**Provider:** Qwen Code API (recommended)
- **Model:** `qwen3-coder-plus`
- **Reason:** 1000 free requests/day, works from Russia, no credit card required
- **API Compatibility:** OpenAI-compatible chat completions API

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  CLI Input  │ ──► │   agent.py   │ ──► │  LLM API    │ ──► │  JSON Output │
│  (question) │     │  (parser +   │     │  (Qwen)     │     │  {answer,    │
│             │     │   formatter) │     │             │     │   tool_calls}│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## Components

### 1. Environment Configuration (`.env.agent.secret`)
- `LLM_API_KEY`: API key for authentication
- `LLM_API_BASE`: Base URL for the LLM API endpoint
- `LLM_MODEL`: Model name to use (default: `qwen3-coder-plus`)

### 2. Agent (`agent.py`)
- **Input:** Question as first command-line argument
- **Process:**
  1. Parse command-line arguments
  2. Load environment configuration
  3. Build OpenAI-compatible API request
  4. Call LLM API with timeout (60 seconds)
  5. Parse response and format as JSON
- **Output:** Single JSON line to stdout with `answer` and `tool_calls` fields

### 3. Output Format
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Implementation Details

### Dependencies
- `httpx` or `requests` for HTTP calls
- `python-dotenv` for environment variable loading
- Standard library: `argparse`, `json`, `sys`, `os`

### Error Handling
- API errors → stderr message, exit code 1
- Timeout (>60s) → stderr message, exit code 1
- Invalid input → stderr message, exit code 1
- Success → exit code 0

### stdout vs stderr
- **stdout:** Only valid JSON response
- **stderr:** All debug/progress/error messages

## Testing Strategy

### Regression Test
- Run `agent.py` as subprocess with test question
- Parse stdout as JSON
- Verify `answer` field exists and is non-empty
- Verify `tool_calls` field exists and is an array

## Files to Create

1. `plans/task-1.md` - This implementation plan
2. `agent.py` - Main CLI agent
3. `.env.agent.secret` - Environment configuration (from `.env.agent.example`)
4. `AGENT.md` - Documentation
5. `tests/test_agent.py` - Regression test

## Acceptance Criteria

- [ ] `plans/task-1.md` exists with implementation plan
- [ ] `agent.py` exists in project root
- [ ] `uv run agent.py "..."` outputs valid JSON with `answer` and `tool_calls`
- [ ] API key stored in `.env.agent.secret` (not hardcoded)
- [ ] `AGENT.md` documents the solution architecture
- [ ] 1 regression test exists and passes
