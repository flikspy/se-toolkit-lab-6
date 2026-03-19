# Agent CLI Documentation

## Overview

`agent.py` is a Python CLI that connects to an LLM API and returns structured JSON responses. This is the foundation for the agentic system - currently it only calls the LLM without tools or agentic loop.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  CLI Input  │ ──► │   agent.py   │ ──► │  LLM API    │ ──► │  JSON Output │
│  (question) │     │  (parser +   │     │  (Qwen)     │     │  {answer,    │
│             │     │   formatter) │     │             │     │   tool_calls}│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

## LLM Provider

**Provider:** Qwen Code API
- **Model:** `qwen3-coder-plus` (default)
- **API Compatibility:** OpenAI-compatible chat completions API
- **Free Tier:** 1000 requests per day

### Alternative Providers

You can use any LLM provider that supports the OpenAI-compatible API:
- **OpenRouter:** Multiple models available
- **Local models:** Via Ollama, LM Studio, etc.

## Configuration

### Environment File

Create `.env.agent.secret` from the example:

```bash
cp .env.agent.example .env.agent.secret
```

Edit `.env.agent.secret`:

```bash
# Your LLM provider API key
LLM_API_KEY=your-llm-api-key-here

# API base URL (OpenAI-compatible endpoint)
# For Qwen Code API on your VM:
LLM_API_BASE=http://<your-vm-ip>:<qwen-api-port>/v1
# For OpenRouter:
# LLM_API_BASE=https://openrouter.ai/api/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LLM_API_KEY` | API key for authentication | Yes | - |
| `LLM_API_BASE` | Base URL for LLM API | Yes | - |
| `LLM_MODEL` | Model name to use | No | `qwen3-coder-plus` |

## Usage

### Basic Usage

```bash
uv run agent.py "What does REST stand for?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Output Format

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `tool_calls` | array | Empty array (tools not implemented yet) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API error, timeout) |

### stdout vs stderr

- **stdout:** Only valid JSON response
- **stderr:** All debug/progress/error messages

## Implementation Details

### Dependencies

- `httpx` - HTTP client for API calls
- `python-dotenv` - Environment variable loading
- Standard library: `argparse`, `json`, `sys`, `os`, `pathlib`

### Timeout

The agent has a 60-second timeout for LLM API requests.

### Error Handling

- Missing API key → stderr message, exit code 1
- Missing API base URL → stderr message, exit code 1
- API timeout → stderr message, exit code 1
- API error → stderr message, exit code 1
- Network error → stderr message, exit code 1

## Testing

### Manual Testing

```bash
# Test with a simple question
uv run agent.py "What is 2 + 2?"

# Test with a knowledge question
uv run agent.py "What does REST stand for?"
```

### Automated Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

## Future Enhancements

This is the foundation for the agentic system. Future tasks will add:

1. **Task 2:** Tool integration - populate `tool_calls` array
2. **Task 3:** Agentic loop - multi-turn reasoning with tools
3. **System prompt:** Enhanced domain knowledge and instructions

## Troubleshooting

### "LLM_API_KEY not set"

Ensure `.env.agent.secret` exists and contains `LLM_API_KEY`.

### "LLM_API_BASE not set"

Ensure `.env.agent.secret` exists and contains `LLM_API_BASE`.

### Timeout errors

- Check your network connection
- Verify the LLM API is running
- Consider using a faster model

### API errors

- Verify your API key is correct
- Check the API base URL is correct
- Ensure the model name is valid for your provider
