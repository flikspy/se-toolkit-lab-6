# Task 2: The Documentation Agent - Implementation Plan

## Overview

Extend the agent from Task 1 with **tools** and an **agentic loop**. The agent will be able to read files and list directories from the project wiki to answer questions with proper source references.

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

## Tools

### 1. `read_file`

Read a file from the project repository.

**Schema:**
```json
{
  "name": "read_file",
  "description": "Read the contents of a file from the project",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Accept `path` parameter
- Validate path does not contain `../` (path traversal protection)
- Validate path is within project directory
- Read file contents using `Path.read_text()`
- Return contents as string or error message

### 2. `list_files`

List files and directories at a given path.

**Schema:**
```json
{
  "name": "list_files",
  "description": "List files and directories in a directory",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative directory path from project root (e.g., 'wiki')"
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
- Accept `path` parameter
- Validate path does not contain `../` (path traversal protection)
- Validate path is within project directory
- List directory entries using `Path.iterdir()`
- Return newline-separated listing

## Security: Path Validation

Both tools must validate paths to prevent directory traversal attacks:

1. **Reject paths containing `../`** - prevents parent directory access
2. **Resolve to absolute path** and verify it's within project root
3. **Reject absolute paths** - only relative paths from project root allowed

```python
def validate_path(relative_path: str, project_root: Path) -> Path:
    """Validate and resolve a relative path within project root."""
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
```

## Agentic Loop

The agentic loop implements the following logic:

```python
MAX_TOOL_CALLS = 10
messages = [{"role": "user", "content": question}]

for iteration in range(MAX_TOOL_CALLS):
    # 1. Call LLM with messages and tool schemas
    response = call_llm(messages, tools=tool_schemas)
    
    # 2. Check if LLM wants to call tools
    if response.tool_calls:
        # Execute each tool call
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            # Append tool result as new message
            messages.append({"role": "tool", "content": result})
        # Continue loop
    else:
        # 3. LLM provided final answer
        answer = response.content
        break

# 4. Format and output JSON
output = {
    "answer": answer,
    "source": extract_source(messages),
    "tool_calls": all_tool_calls
}
```

## System Prompt

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

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\n..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Implementation Steps

1. **Define tool schemas** - JSON schemas for OpenAI function calling
2. **Implement tool functions** - `read_file()` and `list_files()` with path validation
3. **Implement tool executor** - Map tool names to functions, execute with args
4. **Implement agentic loop** - Loop up to 10 times, handling tool calls
5. **Update output format** - Add `source` field, populate `tool_calls` with results
6. **Update system prompt** - Guide LLM to use tools and provide source references

## Testing Strategy

### Test 1: Merge Conflict Question
- **Question:** "How do you resolve a merge conflict?"
- **Expected:** 
  - `read_file` in tool_calls
  - `wiki/git-workflow.md` in source

### Test 2: Wiki Files Question
- **Question:** "What files are in the wiki?"
- **Expected:**
  - `list_files` in tool_calls
  - Non-empty tool_calls array

## Files to Update

1. `plans/task-2.md` - This implementation plan
2. `agent.py` - Add tools and agentic loop
3. `AGENT.md` - Document tools and agentic loop
4. `tests/test_agent.py` - Add 2 regression tests

## Acceptance Criteria

- [ ] `plans/task-2.md` exists with implementation plan
- [ ] `agent.py` defines `read_file` and `list_files` as tool schemas
- [ ] The agentic loop executes tool calls and feeds results back
- [ ] `tool_calls` in output is populated when tools are used
- [ ] `source` field correctly identifies wiki section
- [ ] Tools do not access files outside project directory
- [ ] `AGENT.md` documents tools and agentic loop
- [ ] 2 tool-calling regression tests exist and pass
