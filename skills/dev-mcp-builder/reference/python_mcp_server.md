# Python MCP Server Implementation Guide

## Overview

This document provides Python-specific best practices and examples for implementing MCP servers using the MCP Python SDK (FastMCP). It covers server setup, tool registration patterns, input validation with Pydantic, error handling, state management, testing, and complete working examples. Based on the MCP specification (2025-06-18) and our production datalake MCP server patterns.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [MCP Python SDK and FastMCP](#mcp-python-sdk-and-fastmcp)
3. [Server Naming Convention](#server-naming-convention)
4. [Tool Implementation](#tool-implementation)
5. [Pydantic v2 Key Features](#pydantic-v2-key-features)
6. [Response Format Options](#response-format-options)
7. [Pagination Implementation](#pagination-implementation)
8. [Character Limits and Truncation](#character-limits-and-truncation)
9. [Error Handling](#error-handling)
10. [Shared Utilities](#shared-utilities)
11. [Async/Await Best Practices](#asyncawait-best-practices)
12. [Type Hints](#type-hints)
13. [Tool Docstrings](#tool-docstrings)
14. [Complete Example](#complete-example)
15. [Advanced FastMCP Features](#advanced-fastmcp-features)
16. [State Management Pattern](#state-management-pattern)
17. [Custom Exception Hierarchy](#custom-exception-hierarchy)
18. [Separation of Concerns](#separation-of-concerns)
19. [Automated Testing](#automated-testing)
20. [Code Best Practices](#code-best-practices)
21. [Lambda Handler for AgentCore Gateway (Optional)](#lambda-handler-for-agentcore-gateway-optional)
22. [CDK Infrastructure for AgentCore Deployment](#cdk-infrastructure-for-agentcore-deployment)
23. [Quality Checklist](#quality-checklist)

---

## Quick Reference

### Key Imports
```python
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum
import httpx
```

### Server Initialization
```python
# Local development (stdio)
mcp = FastMCP("service_mcp")

# AgentCore Runtime deployment (container) — stateless_http is required
mcp = FastMCP("service_mcp", host="0.0.0.0", stateless_http=True)
```

### Tool Registration Pattern
```python
@mcp.tool(name="service_tool_name", annotations=ToolAnnotations(...))
async def service_tool_name(params: InputModel) -> str:
    # Implementation
    pass
```

---

## MCP Python SDK and FastMCP

The official MCP Python SDK provides FastMCP, a high-level framework for building MCP servers. It provides:
- Automatic description and inputSchema generation from function signatures and docstrings
- Pydantic model integration for input validation
- Decorator-based tool registration with `@mcp.tool`

**For complete SDK documentation, use WebFetch to load:**
`https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`

## Server and Tool Naming

Follow the naming conventions in [MCP Best Practices](./mcp_best_practices.md#1-server-naming-conventions). Key points: package names use `{service}_mcp`, repo names use `bb-mcp-{service}`, tool names use `{service}_{verb}_{noun}` with snake_case.

## Tool Implementation

### Tool Structure with FastMCP

Tools are defined using the `@mcp.tool` decorator with Pydantic models for input validation:

```python
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("example_mcp")

# Define Pydantic model for input validation
class ServiceToolInput(BaseModel):
    '''Input model for service tool operation.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        validate_assignment=True,    # Validate on assignment
        extra='forbid'              # Forbid extra fields
    )

    param1: str = Field(..., description="First parameter description (e.g., 'user123', 'project-abc')", min_length=1, max_length=100)
    param2: Optional[int] = Field(default=None, description="Optional integer parameter with constraints", ge=0, le=1000)
    tags: Optional[List[str]] = Field(default_factory=list, description="List of tags to apply", max_items=10)

@mcp.tool(
    name="service_tool_name",
    annotations=ToolAnnotations(
        title="Human-Readable Tool Title",
        readOnlyHint=True,         # Tool does not modify environment
        destructiveHint=False,     # Tool does not perform destructive operations
        idempotentHint=True,       # Repeated calls have no additional effect
        openWorldHint=False        # Tool does not interact with external entities
    )
)
async def service_tool_name(params: ServiceToolInput) -> str:
    '''Tool description automatically becomes the 'description' field.

    This tool performs a specific operation on the service. It validates all inputs
    using the ServiceToolInput Pydantic model before processing.

    Args:
        params (ServiceToolInput): Validated input parameters containing:
            - param1 (str): First parameter description
            - param2 (Optional[int]): Optional parameter with default
            - tags (Optional[List[str]]): List of tags

    Returns:
        str: JSON-formatted response containing operation results
    '''
    # Implementation here
    pass
```

## Pydantic v2 Key Features

- Use `model_config` instead of nested `Config` class
- Use `field_validator` instead of deprecated `validator`
- Use `model_dump()` instead of deprecated `dict()`
- Validators require `@classmethod` decorator
- Type hints are required for validator methods

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class CreateUserInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    name: str = Field(..., description="User's full name", min_length=1, max_length=100)
    email: str = Field(..., description="User's email address", pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(..., description="User's age", ge=0, le=150)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Email cannot be empty")
        return v.lower()
```

## Response Format Options

Support multiple output formats for flexibility:

```python
from enum import Enum

class ResponseFormat(str, Enum):
    '''Output format for tool responses.'''
    MARKDOWN = "markdown"
    JSON = "json"

class UserSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )
```

See [MCP Best Practices: Response Format Guidelines](./mcp_best_practices.md#3-response-format-guidelines) for when to use each format.

## Pagination Implementation

For tools that list resources (see [MCP Best Practices: Pagination](./mcp_best_practices.md#4-pagination-best-practices) for general guidelines):

```python
class ListInput(BaseModel):
    limit: Optional[int] = Field(default=20, description="Maximum results to return", ge=1, le=100)
    offset: Optional[int] = Field(default=0, description="Number of results to skip for pagination", ge=0)

async def list_items(params: ListInput) -> str:
    # Make API request with pagination
    data = await api_request(limit=params.limit, offset=params.offset)

    # Return pagination info
    response = {
        "total": data["total"],
        "count": len(data["items"]),
        "offset": params.offset,
        "items": data["items"],
        "has_more": data["total"] > params.offset + len(data["items"]),
        "next_offset": params.offset + len(data["items"]) if data["total"] > params.offset + len(data["items"]) else None
    }
    return json.dumps(response, indent=2)
```

## Character Limits and Truncation

Agents have limited context windows, so unbounded responses waste their budget and can cause failures. Add a CHARACTER_LIMIT constant (see also [MCP Best Practices: Character Limits](./mcp_best_practices.md#5-character-limits-and-truncation)):

```python
# At module level
CHARACTER_LIMIT = 25000  # Maximum response size in characters

async def search_tool(params: SearchInput) -> str:
    result = generate_response(data)

    # Check character limit and truncate if needed
    if len(result) > CHARACTER_LIMIT:
        # Truncate data and add notice
        truncated_data = data[:max(1, len(data) // 2)]
        response["data"] = truncated_data
        response["truncated"] = True
        response["truncation_message"] = (
            f"Response truncated from {len(data)} to {len(truncated_data)} items. "
            f"Use 'offset' parameter or add filters to see more results."
        )
        result = json.dumps(response, indent=2)

    return result
```

## Error Handling

Provide clear, actionable error messages:

```python
def _handle_api_error(e: Exception) -> str:
    '''Consistent error formatting across all tools.'''
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return "Error: Resource not found. Please check the ID is correct."
        elif e.response.status_code == 403:
            return "Error: Permission denied. You don't have access to this resource."
        elif e.response.status_code == 429:
            return "Error: Rate limit exceeded. Please wait before making more requests."
        return f"Error: API request failed with status {e.response.status_code}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Please try again."
    return f"Error: Unexpected error occurred: {type(e).__name__}"
```

## Shared Utilities

Extract common functionality into reusable functions:

```python
# Shared API request function
async def _make_api_request(endpoint: str, method: str = "GET", **kwargs) -> dict:
    '''Reusable function for all API calls.'''
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            f"{API_BASE_URL}/{endpoint}",
            timeout=30.0,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
```

## Async/Await Best Practices

Always use async/await for network requests and I/O operations:

```python
# Good: Async network request
async def fetch_data(resource_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/resource/{resource_id}")
        response.raise_for_status()
        return response.json()

# Bad: Synchronous request
def fetch_data(resource_id: str) -> dict:
    response = requests.get(f"{API_URL}/resource/{resource_id}")  # Blocks
    return response.json()
```

## Type Hints

Use type hints throughout:

```python
from typing import Optional, List, Dict, Any

async def get_user(user_id: str) -> Dict[str, Any]:
    data = await fetch_user(user_id)
    return {"id": data["id"], "name": data["name"]}
```

## Tool Docstrings

Docstrings are the primary way agents discover what a tool does, what inputs it expects, and when to use it vs. alternatives. FastMCP automatically converts docstrings into the tool's `description` field. Thorough docstrings with explicit type information make agents significantly more effective:

```python
async def search_users(params: UserSearchInput) -> str:
    '''
    Search for users in the Example system by name, email, or team.

    This tool searches across all user profiles in the Example platform,
    supporting partial matches and various search filters. It does NOT
    create or modify users, only searches existing ones.

    Args:
        params (UserSearchInput): Validated input parameters containing:
            - query (str): Search string to match against names/emails (e.g., "john", "@example.com", "team:marketing")
            - limit (Optional[int]): Maximum results to return, between 1-100 (default: 20)
            - offset (Optional[int]): Number of results to skip for pagination (default: 0)

    Returns:
        str: JSON-formatted string containing search results with the following schema:

        Success response:
        {
            "total": int,           # Total number of matches found
            "count": int,           # Number of results in this response
            "offset": int,          # Current pagination offset
            "users": [
                {
                    "id": str,      # User ID (e.g., "U123456789")
                    "name": str,    # Full name (e.g., "John Doe")
                    "email": str,   # Email address (e.g., "john@example.com")
                    "team": str     # Team name (e.g., "Marketing") - optional
                }
            ]
        }

        Error response:
        "Error: <error message>" or "No users found matching '<query>'"

    Examples:
        - Use when: "Find all marketing team members" -> params with query="team:marketing"
        - Use when: "Search for John's account" -> params with query="john"
        - Don't use when: You need to create a user (use example_create_user instead)
        - Don't use when: You have a user ID and need full details (use example_get_user instead)

    Error Handling:
        - Input validation errors are handled by Pydantic model
        - Returns "Error: Rate limit exceeded" if too many requests (429 status)
        - Returns "Error: Invalid API authentication" if API key is invalid (401 status)
        - Returns formatted list of results or "No users found matching 'query'"
    '''
```

## Complete Example

See below for a complete Python MCP server example:

```python
#!/usr/bin/env python3
'''
MCP Server for Example Service.

This server provides tools to interact with Example API, including user search,
project management, and data export capabilities.
'''

from typing import Optional, List, Dict, Any
from enum import Enum
import json
import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import ToolAnnotations

# Initialize the MCP server
mcp = FastMCP("example_mcp")

# Constants
API_BASE_URL = "https://api.example.com/v1"
CHARACTER_LIMIT = 25000  # Maximum response size in characters

# Shared annotation sets for consistent tool metadata
_READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True
)

_WRITE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True
)

# Enums
class ResponseFormat(str, Enum):
    '''Output format for tool responses.'''
    MARKDOWN = "markdown"
    JSON = "json"

# Pydantic Models for Input Validation
class UserSearchInput(BaseModel):
    '''Input model for user search operations.'''
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    query: str = Field(..., description="Search string to match against names/emails", min_length=2, max_length=200)
    limit: Optional[int] = Field(default=20, description="Maximum results to return", ge=1, le=100)
    offset: Optional[int] = Field(default=0, description="Number of results to skip for pagination", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

# Shared utility functions
async def _make_api_request(endpoint: str, method: str = "GET", **kwargs) -> dict:
    '''Reusable function for all API calls.'''
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            f"{API_BASE_URL}/{endpoint}",
            timeout=30.0,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

def _handle_api_error(e: Exception) -> str:
    '''Consistent error formatting with recovery guidance.'''
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return "Error: Resource not found. Action: Verify the ID is correct using a list or search tool."
        elif e.response.status_code == 403:
            return "Error: Permission denied. Action: Check your access level for this resource."
        elif e.response.status_code == 429:
            return "Error: Rate limit exceeded. Action: Wait 30 seconds before retrying."
        return f"Error: API request failed with status {e.response.status_code}."
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Action: Try again or reduce the scope of your query."
    return f"Error: Unexpected error occurred: {type(e).__name__}"

# Tool definitions
@mcp.tool(
    name="example_search_users",
    annotations=_READ_ONLY_ANNOTATIONS
)
async def example_search_users(params: UserSearchInput) -> str:
    '''Search for users in the Example system by name, email, or team.

    [Full docstring as shown above]
    '''
    try:
        # Make API request using validated parameters
        data = await _make_api_request(
            "users/search",
            params={
                "q": params.query,
                "limit": params.limit,
                "offset": params.offset
            }
        )

        users = data.get("users", [])
        total = data.get("total", 0)

        if not users:
            return f"No users found matching '{params.query}'"

        # Format response based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            lines = [f"# User Search Results: '{params.query}'", ""]
            lines.append(f"Found {total} users (showing {len(users)})")
            lines.append("")

            for user in users:
                lines.append(f"## {user['name']} ({user['id']})")
                lines.append(f"- **Email**: {user['email']}")
                if user.get('team'):
                    lines.append(f"- **Team**: {user['team']}")
                lines.append("")

            return "\n".join(lines)

        else:
            response = {
                "total": total,
                "count": len(users),
                "offset": params.offset,
                "users": users
            }
            return json.dumps(response, indent=2)

    except Exception as e:
        return _handle_api_error(e)

if __name__ == "__main__":
    mcp.run()
```

---

## Advanced FastMCP Features

### Context Parameter Injection

FastMCP can automatically inject a `Context` parameter into tools for advanced capabilities like logging, progress reporting, resource reading, and user interaction:

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("example_mcp")

@mcp.tool()
async def advanced_search(query: str, ctx: Context) -> str:
    '''Advanced tool with context access for logging and progress.'''

    # Report progress for long operations
    await ctx.report_progress(0.25, "Starting search...")

    # Log information for debugging
    await ctx.log_info("Processing query", {"query": query, "timestamp": datetime.now()})

    # Perform search
    results = await search_api(query)
    await ctx.report_progress(0.75, "Formatting results...")

    # Access server configuration
    server_name = ctx.fastmcp.name

    return format_results(results)

@mcp.tool()
async def interactive_tool(resource_id: str, ctx: Context) -> str:
    '''Tool that can request additional input from users.'''

    # Request sensitive information when needed
    api_key = await ctx.elicit(
        prompt="Please provide your API key:",
        input_type="password"
    )

    # Use the provided key
    return await api_call(resource_id, api_key)
```

**Context capabilities:**
- `ctx.report_progress(progress, message)` - Report progress for long operations
- `ctx.log_info(message, data)` / `ctx.log_error()` / `ctx.log_debug()` - Logging
- `ctx.elicit(prompt, input_type)` - Request input from users
- `ctx.fastmcp.name` - Access server configuration
- `ctx.read_resource(uri)` - Read MCP resources

### Resource Registration

Expose data as resources for efficient, template-based access:

```python
@mcp.resource("file://documents/{name}")
async def get_document(name: str) -> str:
    '''Expose documents as MCP resources.

    Resources are useful for static or semi-static data that doesn't
    require complex parameters. They use URI templates for flexible access.
    '''
    document_path = f"./docs/{name}"
    with open(document_path, "r") as f:
        return f.read()

@mcp.resource("config://settings/{key}")
async def get_setting(key: str, ctx: Context) -> str:
    '''Expose configuration as resources with context.'''
    settings = await load_settings()
    return json.dumps(settings.get(key, {}))
```

**When to use Resources vs Tools:**
- **Resources**: For data access with simple parameters (URI templates)
- **Tools**: For complex operations with validation and business logic

### Structured Output Types

FastMCP supports multiple return types beyond strings:

```python
from typing import TypedDict
from dataclasses import dataclass
from pydantic import BaseModel

# TypedDict for structured returns
class UserData(TypedDict):
    id: str
    name: str
    email: str

@mcp.tool()
async def get_user_typed(user_id: str) -> UserData:
    '''Returns structured data - FastMCP handles serialization.'''
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}

# Pydantic models for complex validation
class DetailedUser(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    metadata: Dict[str, Any]

@mcp.tool()
async def get_user_detailed(user_id: str) -> DetailedUser:
    '''Returns Pydantic model - automatically generates schema.'''
    user = await fetch_user(user_id)
    return DetailedUser(**user)
```

### Lifespan Management

Initialize resources that persist across requests:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan():
    '''Manage resources that live for the server's lifetime.'''
    # Initialize connections, load config, etc.
    db = await connect_to_database()
    config = load_configuration()

    # Make available to all tools
    yield {"db": db, "config": config}

    # Cleanup on shutdown
    await db.close()

mcp = FastMCP("example_mcp", lifespan=app_lifespan)

@mcp.tool()
async def query_data(query: str, ctx: Context) -> str:
    '''Access lifespan resources through context.'''
    db = ctx.request_context.lifespan_state["db"]
    results = await db.query(query)
    return format_results(results)
```

### Multiple Transport Options

FastMCP supports different transport mechanisms:

```python
# Default: Stdio transport (for CLI tools, Claude Desktop, Claude Code)
if __name__ == "__main__":
    mcp.run()

# Streamable HTTP transport (for remote/shared servers)
if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)

# AgentCore Runtime deployment — stateless_http=True is REQUIRED
# AgentCore manages sessions; the server must be stateless per-request
mcp = FastMCP("service_mcp", host="0.0.0.0", stateless_http=True)
if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)
```

**Transport selection:**
- **Stdio**: Command-line tools, local development, Claude Desktop/Code integration
- **Streamable HTTP**: Remote servers, cloud deployment, multi-client scenarios
- **Streamable HTTP + `stateless_http=True`**: AWS AgentCore Runtime (container deployment)

> **Note**: The SSE transport is deprecated. Use Streamable HTTP for all new remote deployments.
> **Note**: AgentCore Runtime requires `stateless_http=True` because AgentCore manages session state externally.

---

## State Management Pattern

For MCP servers that need to cache data or maintain connections across requests, use a module-level cached state with async initialization:

```python
from dataclasses import dataclass
import asyncio

@dataclass
class AppState:
    """Container for all server state."""
    config: CustomerConfig
    metadata: MetadataContext
    api_client: SomeClient

_cached_state: AppState | None = None
_state_lock = asyncio.Lock()

async def get_or_create_state() -> AppState:
    """Thread-safe lazy initialization of server state."""
    global _cached_state
    if _cached_state is not None:
        return _cached_state
    async with _state_lock:
        if _cached_state is not None:  # Double-check after acquiring lock
            return _cached_state
        _cached_state = await create_app_state()
        return _cached_state
```

**When to use**: Container-based deployments (AWS AgentCore) where the container persists across requests. Avoids reloading metadata on every invocation.

**Alternative**: For simpler servers, use the FastMCP lifespan pattern instead.

---

## Custom Exception Hierarchy

Define permanent vs transient errors for proper retry behavior:

```python
class ServiceError(Exception):
    """Permanent failure — do not retry."""
    pass

class TransientServiceError(Exception):
    """Retryable failure — throttling, timeouts, connection errors."""
    pass

def classify_error(error: Exception) -> Exception:
    """Classify external errors as permanent or transient."""
    if hasattr(error, 'response'):
        status = error.response.status_code
        if status in (429, 502, 503, 504):
            return TransientServiceError(str(error))
    if "timeout" in str(error).lower() or "connection" in str(error).lower():
        return TransientServiceError(str(error))
    return ServiceError(str(error))
```

### Retry with Backoff

Use `tenacity` for automatic retry of transient errors:

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

@retry(
    retry=retry_if_exception_type(TransientServiceError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
async def execute_with_retry(operation):
    try:
        return await operation()
    except Exception as e:
        raise classify_error(e)
```

---

## Separation of Concerns

Keep core tool logic transport-agnostic — if it imports FastMCP or Lambda-specific modules, you can't reuse it across deployment targets. This pattern enables the same business logic to serve both the FastMCP server and Lambda handlers:

```python
# core/tools.py — Transport-agnostic business logic
def tool_list_tables(state: AppState) -> str:
    """Pure business logic, no MCP dependencies."""
    tables = state.metadata.get_all_tables()
    return format_table_list(tables)

# server.py — MCP server wrapper
@mcp.tool(name="service_list_tables", annotations=_READ_ONLY_ANNOTATIONS)
async def service_list_tables() -> str:
    state = await get_or_create_state()
    cid = generate_correlation_id()
    with audit_tool_call("service_list_tables", cid, customer_id):
        return tool_list_tables(state)

# lambda_handler.py — Lambda wrapper (same core logic)
def handle_list_tables(event, state):
    return tool_list_tables(state)
```

---

## Automated Testing

### FastMCP In-Memory Testing

Test tools directly without subprocess management using FastMCP's built-in test client:

```python
import pytest
from fastmcp import Client

@pytest.fixture
async def mcp_client():
    """Create test client connected directly to the FastMCP server."""
    async with Client(transport=mcp) as client:
        yield client

async def test_list_tables(mcp_client):
    result = await mcp_client.call_tool("service_list_tables", {})
    assert len(result) > 0
    assert result[0].type == "text"
    assert "table_name" in result[0].text

async def test_invalid_input(mcp_client):
    result = await mcp_client.call_tool("service_search", {"query": ""})
    assert "Error" in result[0].text

async def test_not_found_suggests_alternatives(mcp_client):
    result = await mcp_client.call_tool("service_describe", {"name": "tabel_nme"})
    assert "Did you mean" in result[0].text
```

### Test Organization

```
tests/
├── conftest.py                # Shared fixtures (mcp_client, mock state, sample data)
├── unit/
│   ├── test_core_tools.py     # Transport-agnostic tool logic
│   ├── test_input_validation.py
│   └── test_error_handling.py
├── integration/
│   ├── test_aws_services.py   # @pytest.mark.integration
│   └── test_end_to_end.py     # @pytest.mark.integration
└── conftest.py
```

### Quality Gate Commands

```bash
uv run ruff check .                    # Linting
uv run ruff format --check .           # Format check
uv run mypy src/                       # Type checking (strict)
uv run bandit -r src/                  # Security scanning
uv run pytest -m "not integration"     # Unit tests
uv run pytest --cov --cov-report=html  # Coverage report
```

---

## Code Best Practices

### Code Composability and Reusability

Prioritize composability and code reuse — MCP servers tend to have many tools with overlapping patterns, so duplication compounds quickly:

1. **Extract Common Functionality**:
   - Create reusable helper functions for operations used across multiple tools
   - Build shared API clients for HTTP requests instead of duplicating code
   - Centralize error handling logic in utility functions
   - Extract business logic into dedicated functions that can be composed
   - Extract shared markdown or JSON field selection & formatting functionality

2. **Avoid Duplication**:
   - NEVER copy-paste similar code between tools
   - If you find yourself writing similar logic twice, extract it into a function
   - Common operations like pagination, filtering, field selection, and formatting should be shared
   - Authentication/authorization logic should be centralized

### Python-Specific Best Practices

1. **Use Type Hints**: Always include type annotations for function parameters and return values
2. **Pydantic Models**: Define clear Pydantic models for all input validation
3. **Avoid Manual Validation**: Let Pydantic handle input validation with constraints
4. **Proper Imports**: Group imports (standard library, third-party, local)
5. **Error Handling**: Use specific exception types (httpx.HTTPStatusError, not generic Exception)
6. **Async Context Managers**: Use `async with` for resources that need cleanup
7. **Constants**: Define module-level constants in UPPER_CASE

## Lambda Handler for AgentCore Gateway (Optional)

> **Note**: This section only applies when using the **Gateway Lambda target** deployment path. If deploying via AgentCore Runtime (container), the FastMCP server itself handles requests — no Lambda handler is needed.

The Lambda handler enables AWS Bedrock AgentCore Gateway to invoke your MCP tools via Lambda. It reuses the same core tool logic as the FastMCP server.

### Handler Architecture

```python
"""Lambda entry point for AgentCore Gateway invocation."""
import json
import logging
from typing import Any

from .core.state import AppState, create_app_state_sync
from .core.tools import tool_ping, tool_list_tables, tool_run_query
from .core.audit import generate_correlation_id, audit_tool_call

logger = logging.getLogger(__name__)

# Module-level cache for Lambda container reuse
_cached_state: AppState | None = None
CUSTOMER_ID = os.environ.get("CUSTOMER_ID", "default")

def _get_state() -> AppState:
    """Lazy-initialize state, cached across Lambda invocations."""
    global _cached_state
    if _cached_state is None:
        _cached_state = create_app_state_sync()
    return _cached_state

# Tool dispatch table — maps tool names to core functions
TOOLS: dict[str, Any] = {
    "service_ping": lambda state, args: tool_ping(state),
    "service_list_tables": lambda state, args: tool_list_tables(state),
    "service_run_query": lambda state, args: tool_run_query(
        state, args.get("sql", ""), args.get("limit", 100),
        args.get("response_format", "markdown"),
        execute_query=execute_query_sync,
    ),
    # ... add all tools
}
```

### AgentCore Event Extraction

AgentCore Gateway sends tool information in the Lambda context, not the event body:

```python
def _extract_tool_from_context(context) -> tuple[str, dict]:
    """Extract tool name and input from AgentCore Gateway context."""
    custom = json.loads(context.client_context.custom)
    raw_name = custom.get("bedrockAgentCoreToolName", "")
    tool_input = custom.get("bedrockAgentCoreToolInput", {})

    # Strip gateway prefix: "bb-service-customer-env___tool_name" -> "tool_name"
    tool_name = raw_name.split("___")[-1] if "___" in raw_name else raw_name

    return tool_name, tool_input


def handler(event: dict, context: Any) -> dict:
    """Lambda handler supporting both standard and AgentCore formats."""
    state = _get_state()

    # Try event body first, fall back to client_context
    if event and event.get("name"):
        tool_name = event["name"]
        tool_input = event.get("input", {})
    else:
        tool_name, tool_input = _extract_tool_from_context(context)

    if tool_name not in TOOLS:
        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}

    cid = generate_correlation_id()
    with audit_tool_call(tool_name, cid, CUSTOMER_ID):
        result = TOOLS[tool_name](state, tool_input)

    return {"content": [{"type": "text", "text": result}]}
```

### Key Lambda Patterns

1. **Module-level state caching**: Lambda containers persist between invocations — cache AppState globally
2. **Sync execution**: Lambda handler is synchronous (no async/await)
3. **Dual event format**: Support both standard `{"name": ..., "input": ...}` and AgentCore `client_context` formats
4. **Gateway prefix stripping**: Tool names arrive prefixed with target ID, split on `___`
5. **Same core functions**: Dispatch table calls the exact same functions as FastMCP server

---

## CDK Infrastructure for AgentCore Deployment

### Quickstart: AgentCore Starter Toolkit (No CDK)

The simplest deployment path uses the `bedrock-agentcore-starter-toolkit` CLI:

```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure    # Set up AWS credentials and region
agentcore deploy       # Deploy MCP server container to AgentCore Runtime
agentcore invoke       # Test the deployed server
agentcore destroy      # Clean up resources
```

This handles ECR, CodeBuild, and CfnRuntime creation automatically. Use CDK (below) for production deployments requiring custom IAM, monitoring, or multi-environment support.

### IAM Role (Multi-Principal Trust)

The MCP server IAM role must trust multiple principals for dual-transport support:

```python
from aws_cdk import aws_iam as iam

role = iam.Role(
    self, "MCPRole",
    role_name=f"MCPRole-{customer_id}-{environment}",
    assumed_by=iam.CompositePrincipal(
        iam.ServicePrincipal("lambda.amazonaws.com"),
        iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        iam.ServicePrincipal("bedrock.amazonaws.com"),
        iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    ),
)

# Add service-specific permissions (least privilege)
role.add_to_policy(iam.PolicyStatement(
    actions=["logs:CreateLogStream", "logs:PutLogEvents"],
    resources=[log_group.log_group_arn],
))
```

### Lambda Function

```python
from aws_cdk import aws_lambda as lambda_

fn = lambda_.Function(
    self, "MCPFunction",
    function_name=f"bb-mcp-{service}-{customer_id}-{environment}",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler=f"{service}_mcp.lambda_handler.handler",
    code=lambda_.Code.from_asset("src", bundling=...),
    timeout=Duration.minutes(5),
    memory_size=512,
    role=role,
    environment={
        "CUSTOMER_ID": customer_id,
        "ENVIRONMENT": environment,
    },
)
```

### AgentCore Gateway Target

Register the Lambda as a Gateway Target with tool schemas:

```python
from aws_cdk import aws_bedrock as bedrock

# Only create if gateway exists
if gateway_id:
    # Grant AgentCore permission to invoke Lambda
    fn.add_permission(
        "AgentCoreInvoke",
        principal=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
        action="lambda:InvokeFunction",
    )

    # Register as gateway target with tool schemas
    target = bedrock.CfnGatewayTarget(
        self, "GatewayTarget",
        gateway_identifier=gateway_id,
        name=f"bb-{service}-{customer_id}-{environment}",
        target_configuration=bedrock.CfnGatewayTarget.TargetConfigurationProperty(
            mcp_target_configuration=bedrock.CfnGatewayTarget.McpTargetConfigurationProperty(
                lambda_target_configuration=bedrock.CfnGatewayTarget.LambdaTargetConfigurationProperty(
                    lambda_arn=fn.function_arn,
                ),
                # Tool schemas tell the gateway what tools this target provides
                tool_schemas=[
                    bedrock.CfnGatewayTarget.ToolSchemaProperty(
                        tool_name="service_ping",
                        description="Verify server connectivity",
                        input_schema={"type": "object", "properties": {}},
                    ),
                    bedrock.CfnGatewayTarget.ToolSchemaProperty(
                        tool_name="service_run_query",
                        description="Execute a read-only query",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "sql": {"type": "string"},
                                "limit": {"type": "integer", "default": 100},
                            },
                            "required": ["sql"],
                        },
                    ),
                    # ... declare all tool schemas
                ],
            ),
        ),
        credential_provider_configurations=[
            bedrock.CfnGatewayTarget.CredentialProviderConfigurationProperty(
                credential_provider_type="GATEWAY_IAM_ROLE",
            )
        ],
    )
```

### AgentCore Runtime (Container Deployment — Primary Path)

Deploy the FastMCP server as a Docker container to AgentCore Runtime using CfnRuntime:

```python
from aws_cdk import aws_bedrock as bedrock, aws_ecr as ecr, aws_codebuild as codebuild

# ECR repository for MCP server container
repository = ecr.Repository(
    self, "MCPRepo",
    repository_name=f"bb-mcp-{service}-{customer_id}-{environment}",
    removal_policy=RemovalPolicy.DESTROY,
)

# CodeBuild project to build and push Docker image
build_project = codebuild.Project(
    self, "MCPBuild",
    build_spec=codebuild.BuildSpec.from_object({
        "version": "0.2",
        "phases": {
            "build": {
                "commands": [
                    "docker build -t $REPO_URI:latest .",
                    "docker push $REPO_URI:latest",
                ]
            }
        }
    }),
    environment=codebuild.BuildEnvironment(
        privileged=True,  # Required for Docker builds
    ),
)

# AgentCore Runtime — registers the container as an MCP server
runtime = bedrock.CfnRuntime(
    self, "MCPRuntime",
    name=f"bb-mcp-{service}-{customer_id}-{environment}",
    role_arn=role.role_arn,
    network_configuration=bedrock.CfnRuntime.NetworkConfigurationProperty(
        network_mode="PUBLIC",
    ),
    runtime_configuration=bedrock.CfnRuntime.RuntimeConfigurationProperty(
        container_configuration=bedrock.CfnRuntime.ContainerConfigurationProperty(
            container_uri=f"{repository.repository_uri}:latest",
            environment_variables={
                "CUSTOMER_ID": customer_id,
                "ENVIRONMENT": environment,
            },
        ),
    ),
    protocol_configuration=bedrock.CfnRuntime.ProtocolConfigurationProperty(
        server_protocol="MCP",
    ),
)
```

**Dockerfile for AgentCore Runtime:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY src/ src/
# AgentCore Runtime expects MCP server on 0.0.0.0:8000/mcp
EXPOSE 8000
CMD ["python", "-m", "service_mcp.server"]
```

**Server configuration for AgentCore Runtime:**

```python
# server.py — stateless_http=True is REQUIRED for AgentCore Runtime
mcp = FastMCP("service_mcp", host="0.0.0.0", stateless_http=True)

# ... tool definitions ...

if __name__ == "__main__":
    mcp.run(transport="streamable_http", port=8000)
```

### AgentCore Gateway Target (Lambda — Secondary Path)

The existing Lambda + CfnGatewayTarget pattern (shown above) is the secondary deployment path, used when exposing existing Lambda functions as MCP tools through the AgentCore Gateway.

### Gateway Auto-Detection in deploy.sh

```bash
# Auto-detect AgentCore Gateway by name pattern
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways \
    --query "items[?contains(name, '${CUSTOMER_ID}') && contains(name, '${ENVIRONMENT}')].gatewayId | [0]" \
    --output text 2>/dev/null || echo "")

if [ -n "$GATEWAY_ID" ] && [ "$GATEWAY_ID" != "None" ]; then
    echo "Found gateway: $GATEWAY_ID"
    export GATEWAY_ID
fi
```

### Deployment Architecture Summary

```
Local Development:
  Claude Code/Desktop → stdio → FastMCP server.py → core/tools.py

Production (Primary — AgentCore Runtime):
  AgentCore Runtime → Container HTTP → FastMCP server.py (stateless_http=True) → core/tools.py

Production (Secondary — Gateway Lambda):
  AgentCore Gateway → Lambda invoke → lambda_handler.py → core/tools.py
```

All paths use the same transport-agnostic tool logic in `core/tools.py`.

---

## Quality Checklist

Before finalizing your Python MCP server implementation, ensure:

### Strategic Design
- [ ] Tools enable complete workflows, not just API endpoint wrappers
- [ ] Tool names reflect natural task subdivisions
- [ ] Response formats optimize for agent context efficiency
- [ ] Human-readable identifiers used where appropriate
- [ ] Error messages guide agents toward correct usage

### Implementation Quality
- [ ] FOCUSED IMPLEMENTATION: Most important and valuable tools implemented
- [ ] All tools have descriptive names and documentation
- [ ] Return types are consistent across similar operations
- [ ] Error handling is implemented for all external calls
- [ ] Server name follows format: `{service}_mcp`
- [ ] All network operations use async/await
- [ ] Common functionality is extracted into reusable functions
- [ ] Error messages are clear, actionable, and educational
- [ ] Outputs are properly validated and formatted

### Tool Configuration
- [ ] All tools implement 'name' and 'annotations' in the decorator
- [ ] Annotations correctly set (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- [ ] All tools use Pydantic BaseModel for input validation with Field() definitions
- [ ] All Pydantic Fields have explicit types and descriptions with constraints
- [ ] All tools have comprehensive docstrings with explicit input/output types
- [ ] Docstrings include complete schema structure for dict/JSON returns
- [ ] Pydantic models handle input validation (no manual validation needed)

### Architecture (Brain Bridge Standard)
- [ ] Core tool logic in `core/tools.py` is transport-agnostic
- [ ] State management uses AppState pattern with async initialization (if stateful)
- [ ] Custom exception hierarchy (permanent vs transient errors)
- [ ] Retry with exponential backoff for transient errors (tenacity)
- [ ] Audit logging with correlation IDs on every tool call
- [ ] Error messages include recovery action guidance

### Advanced Features (where applicable)
- [ ] Context injection used for logging, progress, or elicitation
- [ ] Resources registered for appropriate data endpoints
- [ ] Lifespan management implemented for persistent connections
- [ ] Structured output types used (TypedDict, Pydantic models)
- [ ] Appropriate transport configured (stdio or Streamable HTTP)

### Code Quality
- [ ] File includes proper imports including Pydantic and ToolAnnotations
- [ ] Pagination is properly implemented where applicable
- [ ] Large responses check CHARACTER_LIMIT and truncate with clear messages
- [ ] Filtering options are provided for potentially large result sets
- [ ] All async functions are properly defined with `async def`
- [ ] HTTP client usage follows async patterns with proper context managers
- [ ] Type hints are used throughout the code
- [ ] Constants are defined at module level in UPPER_CASE

### Testing
- [ ] FastMCP in-memory tests using `Client(transport=mcp)`
- [ ] Unit tests with mocked dependencies (no external service calls)
- [ ] Integration tests marked with `@pytest.mark.integration`
- [ ] All quality gates pass: ruff, mypy, bandit, pytest
- [ ] Minimum 90% unit test coverage
- [ ] Error scenarios handled gracefully with recovery guidance

### Deployment (AgentCore)

**Container Path (AgentCore Runtime — Primary):**
- [ ] `stateless_http=True` set on FastMCP constructor
- [ ] Dockerfile exposes `0.0.0.0:8000/mcp` endpoint
- [ ] CfnRuntime resource configured with proper auth and protocol
- [ ] ECR repository and CodeBuild project for container image
- [ ] IAM role trusts: AgentCore, Bedrock, ECS principals

**Lambda Path (Gateway Target — Secondary):**
- [ ] Lambda handler implements tool dispatch table
- [ ] Handler supports both standard and AgentCore event formats
- [ ] Gateway prefix stripping works (split on `___`)
- [ ] Module-level state caching for container reuse
- [ ] CDK stack creates: IAM role, Lambda, CloudWatch, Gateway Target
- [ ] IAM role trusts: Lambda, AgentCore, Bedrock, ECS principals
- [ ] Tool schemas declared in CDK Gateway Target configuration

**Both Paths:**
- [ ] deploy.sh auto-detects gateway and supports parallel CDK + Docker builds
- [ ] CloudWatch log groups with metrics and error filters