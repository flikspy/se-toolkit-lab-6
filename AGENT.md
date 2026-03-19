# Agent CLI Documentation

## Overview

`agent.py` is a Python CLI that connects to an LLM API with **tools** and an **agentic loop**. The agent can read files and list directories from the project wiki to answer questions with proper source references.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Question   │ ──► │   agent.py   │ ──► │  LLM API    │
│             │     │  (agentic    │     │  (with tool │
│             │     │   loop)      │     │   schemas)  │
└─────────────┘     └───────┬───────┘     └──────┬──────┘
                            │                    │
                            │◄──── tool_calls ───│
                            ▼                    │
                     ┌──────────────┐            │
                     │ Execute tool │            │
                     │ (read_file,  │            │
                     │  list_files) │            │
                     └───────┬──────┘            │
                             │                   │
                             │◄──── result ──────│
                             ▼                   │
                      ┌──────────────┐           │
                      │ Append as    │           │
                      │ tool message │           │
                      └───────┬──────┘           │
                              │                  │
                              └───── loop ──────┘
                                      │
                                      ▼ (no more tool calls)
                               ┌──────────────┐
                               │ Extract      │
                               │ answer +     │
                               │ source       │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │ JSON Output  │
                               └──────────────┘
```

## LLM Provider

**Provider:** OpenRouter (with OpenAI-compatible API)
- **Model:** `nvidia/nemotron-3-nano-30b-a3b:free` (free tier)
- **API Compatibility:** OpenAI-compatible chat completions API with function calling

### Alternative Providers

You can use any LLM provider that supports the OpenAI-compatible API with function calling:
- **Qwen Code API:** Recommended for production use
- **OpenRouter:** Multiple models available
- **Local models:** Via Ollama, LM Studio (if they support function calling)

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
# For OpenRouter:
LLM_API_BASE=https://openrouter.ai/api/v1

# Model name
LLM_MODEL=nvidia/nemotron-3-nano-30b-a3b:free
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
uv run agent.py "How do you resolve a merge conflict?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "To resolve a merge conflict, edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\ngit.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git workflow\n\n..."
    }
  ]
}
```

### Output Format

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The LLM's answer to the question |
| `source` | string | Reference to the wiki section (e.g., `wiki/file.md#section`) |
| `tool_calls` | array | Array of tool calls made during execution |

### Tool Call Format

Each entry in `tool_calls` has:

| Field | Type | Description |
|-------|------|-------------|
| `tool` | string | Name of the tool (`read_file` or `list_files`) |
| `args` | object | Arguments passed to the tool |
| `result` | string | Result returned by the tool |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API error, timeout) |

### stdout vs stderr

- **stdout:** Only valid JSON response
- **stderr:** All debug/progress/error messages

## Tools

The agent has two tools that allow it to interact with the project files.

### `read_file`

Read the contents of a file from the project.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or an error message if the file doesn't exist.

**Example:**
```json
{"tool": "read_file", "args": {"path": "wiki/git.md"}, "result": "# Git\n\n..."}
```

### `list_files`

List files and directories in a directory.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries, or an error message.

**Example:**
```json
{"tool": "list_files", "args": {"path": "wiki"}, "result": "git.md\ngit-workflow.md\n..."}
```

### Security: Path Validation

Both tools validate paths to prevent directory traversal attacks:

1. **Reject paths containing `..`** - prevents parent directory access
2. **Reject absolute paths** - only relative paths from project root allowed
3. **Verify resolved path is within project root** - ensures file is inside the project

## Agentic Loop

The agentic loop implements the following logic:

1. **Send question to LLM** with tool schemas
2. **Check for tool calls:**
   - If LLM returns `tool_calls` → execute each tool, append results as messages, go to step 1
   - If LLM returns text answer → extract answer and source, output JSON, exit
3. **Maximum 10 tool calls** per question to prevent infinite loops

### System Prompt

The system prompt guides the LLM to use tools effectively:

```
You are a documentation agent that answers questions about a software engineering project.

You have access to two tools:
1. list_files - List files in a directory
2. read_file - Read the contents of a file

When answering questions:
1. First use list_files to discover relevant files in the wiki/ directory
2. Then use read_file to read the content of relevant files
3. Find the specific section that answers the question
4. Provide the answer with a source reference in format: wiki/filename.md#section-anchor

Rules:
- Always include a source reference pointing to the wiki file and section
- Use markdown anchors (lowercase, hyphens instead of spaces)
- If you cannot find the answer in the wiki, say so
- Maximum 10 tool calls per question
```

## Implementation Details

### Dependencies

- `httpx` - HTTP client for API calls
- `python-dotenv` - Environment variable loading
- Standard library: `argparse`, `json`, `sys`, `os`, `pathlib`, `re`, `typing`

### Timeout

The agent has a 60-second timeout for each LLM API request.

### Error Handling

- Missing API key → stderr message, exit code 1
- Missing API base URL → stderr message, exit code 1
- API timeout → stderr message, exit code 1
- API error → stderr message, exit code 1
- Network error → stderr message, exit code 1
- Path traversal attempt → error message in tool result

## Testing

### Manual Testing

```bash
# Test with a merge conflict question
uv run agent.py "How do you resolve a merge conflict?"

# Test with a wiki listing question
uv run agent.py "What files are in the wiki?"

# Test with a git question
uv run agent.py "What is the GitHub flow?"
```

### Automated Testing

Run the regression tests:

```bash
uv run pytest tests/test_agent.py -v
```

### Test Cases

1. **Merge conflict question** - expects `read_file` in tool_calls, `wiki/git-vscode.md` or `wiki/git.md` in source
2. **Wiki files question** - expects `list_files` in tool_calls

## Troubleshooting

### "LLM_API_KEY not set"

Ensure `.env.agent.secret` exists and contains `LLM_API_KEY`.

### "LLM_API_BASE not set"

Ensure `.env.agent.secret` exists and contains `LLM_API_BASE`.

### Timeout errors

- Check your network connection
- Verify the LLM API is running
- Consider using a faster model

### API errors (429 Rate Limit)

- You've hit the rate limit for free tier
- Wait a few minutes and try again
- Consider upgrading to a paid tier

### Tool returns "Path traversal not allowed"

The agent blocked access to a path containing `..`. This is a security feature.

### No source in output

The LLM didn't include a source reference. The system prompt instructs it to do so, but the model may occasionally forget.

## Future Enhancements

This agent can be extended with:

1. **More tools:** `search_files`, `grep_content`, `write_file`
2. **Better source extraction:** Parse markdown headers for accurate anchors
3. **Caching:** Cache file contents to reduce redundant reads
4. **Streaming:** Stream tool calls and answers in real-time
5. **Memory:** Remember previous conversations for context
