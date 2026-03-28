# MCP Server Development Best Practices and Guidelines

## Overview

This document compiles essential best practices and guidelines for building Model Context Protocol (MCP) servers. It covers naming conventions, tool design, response formats, pagination, error handling, security, and compliance requirements. Based on the MCP specification (revisions 2025-03-26 and 2025-06-18) and production experience with our MCP servers.

---

## Quick Reference

### Server Naming
- **Format**: `{service}_mcp` (e.g., `slack_mcp`, `datalake_mcp`)
- **Repo name**: `bb-mcp-{service}` (e.g., `bb-mcp-datalake`)

### Tool Naming
- Tool names MUST match regex: `^[a-zA-Z0-9_-]{1,64}$`
- Use snake_case with service prefix
- Format: `{service}_{action}_{resource}`
- Example: `slack_send_message`, `github_create_issue`
- Use separate `title` field for human-readable display names

### Response Formats
- Support both JSON and Markdown formats
- JSON for programmatic processing
- Markdown for human readability

### Pagination
- Always respect `limit` parameter
- Return `has_more`, `next_offset`, `total_count`
- Default to 20-50 items

### Character Limits
- Set CHARACTER_LIMIT constant (typically 25,000)
- Truncate gracefully with clear messages
- Provide guidance on filtering

---

## Table of Contents
1. Server Naming Conventions
2. Tool Naming and Design
3. Response Format Guidelines
4. Pagination Best Practices
5. Character Limits and Truncation
6. Tool Development Best Practices
7. Transport Best Practices
8. Testing Requirements
9. OAuth and Security Best Practices
10. Resource Management Best Practices
11. Prompt Management Best Practices
12. Error Handling Standards
13. Documentation Requirements
14. Compliance and Monitoring
15. Structured Output (New in 2025)
16. Anti-Patterns to Avoid
17. Observability and Logging
18. Brain Bridge Internal Standards

---

## 1. Server Naming Conventions

Follow these standardized naming patterns for MCP servers:

**Package name**: `{service}_mcp` (lowercase with underscores)
- Examples: `datalake_mcp`, `airtable_mcp`, `github_mcp`, `slack_mcp`

**Repository name**: `bb-mcp-{service}` (lowercase with hyphens)
- Examples: `bb-mcp-datalake`, `bb-mcp-bb-os-airtable`

The name should be:
- General (not tied to specific features)
- Descriptive of the service/API being integrated
- Easy to infer from the task description
- Without version numbers or dates

---

## 2. Tool Naming and Design

### Tool Naming Best Practices

1. **Use snake_case**: `search_users`, `create_project`, `get_channel_info`
2. **Include service prefix**: Anticipate that your MCP server may be used alongside other MCP servers
   - Use `slack_send_message` instead of just `send_message`
   - Use `github_create_issue` instead of just `create_issue`
   - Use `asana_list_tasks` instead of just `list_tasks`
3. **Be action-oriented**: Start with verbs (get, list, search, create, etc.)
4. **Be specific**: Avoid generic names that could conflict with other servers
5. **Maintain consistency**: Use consistent naming patterns within your server

### Tool Design Guidelines

- Tool descriptions must narrowly and unambiguously describe functionality
- Descriptions must precisely match actual functionality
- Should not create confusion with other MCP servers
- Should provide tool annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
- Keep tool operations focused and atomic

---

## 3. Response Format Guidelines

All tools that return data should support multiple formats for flexibility:

### JSON Format (`response_format="json"`)
- Machine-readable structured data
- Include all available fields and metadata
- Consistent field names and types
- Suitable for programmatic processing
- Use for when LLMs need to process data further

### Markdown Format (`response_format="markdown"`, typically default)
- Human-readable formatted text
- Use headers, lists, and formatting for clarity
- Convert timestamps to human-readable format (e.g., "2024-01-15 10:30:00 UTC" instead of epoch)
- Show display names with IDs in parentheses (e.g., "@john.doe (U123456)")
- Omit verbose metadata (e.g., show only one profile image URL, not all sizes)
- Group related information logically
- Use for when presenting information to users

---

## 4. Pagination Best Practices

For tools that list resources:

- **Always respect the `limit` parameter**: Never load all results when a limit is specified
- **Implement pagination**: Use `offset` or cursor-based pagination
- **Return pagination metadata**: Include `has_more`, `next_offset`/`next_cursor`, `total_count`
- **Never load all results into memory**: Especially important for large datasets
- **Default to reasonable limits**: 20-50 items is typical
- **Include clear pagination info in responses**: Make it easy for LLMs to request more data

Example pagination response structure:
```json
{
  "total": 150,
  "count": 20,
  "offset": 0,
  "items": [...],
  "has_more": true,
  "next_offset": 20
}
```

---

## 5. Character Limits and Truncation

To prevent overwhelming responses with too much data:

- **Define CHARACTER_LIMIT constant**: Typically 25,000 characters at module level
- **Check response size before returning**: Measure the final response length
- **Truncate gracefully with clear indicators**: Let the LLM know data was truncated
- **Provide guidance on filtering**: Suggest how to use parameters to reduce results
- **Include truncation metadata**: Show what was truncated and how to get more

Example truncation handling:
```python
CHARACTER_LIMIT = 25000

if len(result) > CHARACTER_LIMIT:
    truncated_data = data[:max(1, len(data) // 2)]
    response["truncated"] = True
    response["truncation_message"] = (
        f"Response truncated from {len(data)} to {len(truncated_data)} items. "
        f"Use 'offset' parameter or add filters to see more results."
    )
```

---

## 6. Transport Options

MCP servers support multiple transport mechanisms for different deployment scenarios. The MCP specification (2025-03-26) introduced **Streamable HTTP** as the replacement for the deprecated HTTP+SSE transport.

### Stdio Transport

**Best for**: Command-line tools, local integrations, subprocess execution

**Characteristics**:
- Standard input/output stream communication
- Simple setup, no network configuration needed
- Runs as a subprocess of the client
- Implicit 1:1 session (no session management needed)
- Auth handled by process isolation

**Use when**:
- Building tools for local development environments
- Integrating with desktop applications (e.g., Claude Desktop, Claude Code)
- Creating command-line utilities
- Single-user, single-session scenarios

**Important**: Never write debug output to stdout on stdio transport — it breaks the protocol. Use stderr for logging.

### Streamable HTTP Transport

**Best for**: Remote/shared servers, cloud deployment, multi-client scenarios

**Characteristics**:
- Replaces the deprecated HTTP+SSE transport
- Supports both `application/json` and `text/event-stream` responses
- Explicit session management via `Mcp-Session-Id` header
- Supports resumability and redelivery for reliability
- Requires `MCP-Protocol-Version` header on all requests
- Auth via OAuth 2.0, Bearer tokens, or SigV4

**Use when**:
- Serving multiple clients simultaneously
- Deploying as a cloud service (AWS AgentCore, etc.)
- Integration with web applications
- Need for load balancing, scaling, or session persistence

**Security requirements**:
- Validate the `Origin` header on all incoming connections (prevents DNS rebinding)
- Bind local servers to `127.0.0.1` only, never `0.0.0.0`
- Use cryptographically secure session IDs
- Verify auth on every request (session IDs are NOT authentication)

### Transport Selection Criteria

| Criterion | Stdio | Streamable HTTP |
|-----------|-------|-----------------|
| **Deployment** | Local | Remote |
| **Clients** | Single | Multiple |
| **Session** | Implicit (1:1) | Explicit (Mcp-Session-Id) |
| **Auth** | Process isolation | OAuth 2.0, Bearer, SigV4 |
| **Complexity** | Low | Medium |
| **Resumability** | No | Yes |

> **Note**: The SSE transport is **deprecated** as of spec revision 2025-03-26. Use Streamable HTTP for all new remote deployments. Existing SSE servers should migrate to Streamable HTTP.

---

## 7. Tool Development Best Practices

### General Guidelines
1. Tool names should be descriptive and action-oriented
2. Use parameter validation with detailed JSON schemas
3. Include examples in tool descriptions
4. Implement proper error handling and validation
5. Use progress reporting for long operations
6. Keep tool operations focused and atomic
7. Document expected return value structures
8. Implement proper timeouts
9. Consider rate limiting for resource-intensive operations
10. Log tool usage for debugging and monitoring

### Security Considerations for Tools

#### Input Validation
- Validate all parameters against schema
- Sanitize file paths and system commands
- Validate URLs and external identifiers
- Check parameter sizes and ranges
- Prevent command injection

#### Access Control
- Implement authentication where needed
- Use appropriate authorization checks
- Audit tool usage
- Rate limit requests
- Monitor for abuse

#### Error Handling
- Don't expose internal errors to clients
- Log security-relevant errors
- Handle timeouts appropriately
- Clean up resources after errors
- Validate return values

### Tool Annotations
- Provide readOnlyHint and destructiveHint annotations
- Remember annotations are hints, not security guarantees
- Clients should not make security-critical decisions based solely on annotations

---

## 8. Transport Best Practices

### General Transport Guidelines
1. Handle connection lifecycle properly
2. Implement proper error handling
3. Use appropriate timeout values
4. Implement connection state management
5. Clean up resources on disconnection

### Security Best Practices for Transport
- Follow security considerations for DNS rebinding attacks
- Implement proper authentication mechanisms
- Validate message formats
- Handle malformed messages gracefully

### Stdio Transport Specific
- Local MCP servers should NOT log to stdout (interferes with protocol)
- Use stderr for logging messages
- Handle standard I/O streams properly

---

## 9. Testing Requirements

A comprehensive testing strategy should cover:

### Functional Testing
- Verify correct execution with valid/invalid inputs

### Integration Testing
- Test interaction with external systems

### Security Testing
- Validate auth, input sanitization, rate limiting

### Performance Testing
- Check behavior under load, timeouts

### Error Handling
- Ensure proper error reporting and cleanup

---

## 10. OAuth and Security Best Practices

### Authentication and Authorization

MCP servers that connect to external services should implement proper authentication:

**OAuth 2.1 Implementation:**
- Use secure OAuth 2.1 with certificates from recognized authorities
- Validate access tokens before processing requests
- Only accept tokens specifically intended for your server
- Reject tokens without proper audience claims
- Never pass through tokens received from MCP clients

**API Key Management:**
- Store API keys in environment variables, never in code
- Validate keys on server startup
- Provide clear error messages when authentication fails
- Use secure transmission for sensitive credentials

### Input Validation and Security

**Always validate inputs:**
- Sanitize file paths to prevent directory traversal
- Validate URLs and external identifiers
- Check parameter sizes and ranges
- Prevent command injection in system calls
- Use schema validation (Pydantic) for all inputs

**Error handling security:**
- Don't expose internal errors to clients
- Log security-relevant errors server-side
- Provide helpful but not revealing error messages
- Clean up resources after errors

### Privacy and Data Protection

**Data collection principles:**
- Only collect data strictly necessary for functionality
- Don't collect extraneous conversation data
- Don't collect PII unless explicitly required for the tool's purpose
- Provide clear information about what data is accessed

**Data transmission:**
- Don't send data to servers outside your organization without disclosure
- Use secure transmission (HTTPS) for all network communication
- Validate certificates for external services

---

## 11. Resource Management Best Practices

1. Only suggest necessary resources
2. Use clear, descriptive names for roots
3. Handle resource boundaries properly
4. Respect client control over resources
5. Use model-controlled primitives (tools) for automatic data exposure

---

## 12. Prompt Management Best Practices

- Clients should show users proposed prompts
- Users should be able to modify or reject prompts
- Clients should show users completions
- Users should be able to modify or reject completions
- Consider costs when using sampling

---

## 13. Error Handling Standards

- Use standard JSON-RPC error codes
- Report tool errors within result objects (not protocol-level)
- Provide helpful, specific error messages
- Don't expose internal implementation details
- Clean up resources properly on errors

---

## 14. Documentation Requirements

- Provide clear documentation of all tools and capabilities
- Include working examples (at least 3 per major feature)
- Document security considerations
- Specify required permissions and access levels
- Document rate limits and performance characteristics

---

## 15. Compliance and Monitoring

- Implement logging for debugging and monitoring
- Track tool usage patterns
- Monitor for potential abuse
- Maintain audit trails for security-relevant operations
- Be prepared for ongoing compliance reviews

---

## Summary

These best practices represent the comprehensive guidelines for building secure, efficient, and compliant MCP servers that work well within the ecosystem. Developers should follow these guidelines to ensure their MCP servers meet the standards for inclusion in the MCP directory and provide a safe, reliable experience for users.


----------


# Tools

> Enable LLMs to perform actions through your server

Tools are a powerful primitive in the Model Context Protocol (MCP) that enable servers to expose executable functionality to clients. Through tools, LLMs can interact with external systems, perform computations, and take actions in the real world.

<Note>
  Tools are designed to be **model-controlled**, meaning that tools are exposed from servers to clients with the intention of the AI model being able to automatically invoke them (with a human in the loop to grant approval).
</Note>

## Overview

Tools in MCP allow servers to expose executable functions that can be invoked by clients and used by LLMs to perform actions. Key aspects of tools include:

* **Discovery**: Clients can obtain a list of available tools by sending a `tools/list` request
* **Invocation**: Tools are called using the `tools/call` request, where servers perform the requested operation and return results
* **Flexibility**: Tools can range from simple calculations to complex API interactions

Like [resources](/docs/concepts/resources), tools are identified by unique names and can include descriptions to guide their usage. However, unlike resources, tools represent dynamic operations that can modify state or interact with external systems.

## Tool definition structure

Each tool is defined with the following wire format (JSON-RPC):

```json
{
  "name": "string",
  "description": "string",
  "inputSchema": {
    "type": "object",
    "properties": { "..." : "..." }
  },
  "annotations": {
    "title": "string",
    "readOnlyHint": true,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

## Implementing tools

Here's an example of implementing a basic tool using FastMCP:

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("example_mcp")

@mcp.tool(
    name="example_calculate_sum",
    annotations=ToolAnnotations(
        title="Calculate Sum",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def example_calculate_sum(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number to add
        b: Second number to add
    """
    return str(a + b)
```

## Example tool patterns

Here are examples of tool types a server could provide:

### API integrations

```python
@mcp.tool(name="github_create_issue", annotations=_WRITE_ANNOTATIONS)
async def github_create_issue(
    title: str, body: str, labels: list[str] | None = None
) -> str:
    """Create a GitHub issue in the specified repository."""
    ...
```

### Data querying

```python
@mcp.tool(name="datalake_run_query", annotations=_QUERY_ANNOTATIONS)
async def datalake_run_query(
    sql: str, limit: int = 100, response_format: ResponseFormat = ResponseFormat.MARKDOWN
) -> str:
    """Execute a read-only SQL query against the data lake."""
    ...
```

### Schema/metadata discovery

```python
@mcp.tool(name="service_list_tables", annotations=_READ_ONLY_ANNOTATIONS)
async def service_list_tables() -> str:
    """List all available tables with descriptions and column counts."""
    ...
```

## Best practices

When implementing tools:

1. Provide clear, descriptive names and descriptions
2. Use detailed JSON Schema definitions for parameters
3. Include examples in tool descriptions to demonstrate how the model should use them
4. Implement proper error handling and validation
5. Use progress reporting for long operations
6. Keep tool operations focused and atomic
7. Document expected return value structures
8. Implement proper timeouts
9. Consider rate limiting for resource-intensive operations
10. Log tool usage for debugging and monitoring

### Tool name conflicts

MCP client applications and MCP server proxies may encounter tool name conflicts when building their own tool lists. For example, two connected MCP servers `web1` and `web2` may both expose a tool named `search_web`.

Applications may disambiguiate tools with one of the following strategies (among others; not an exhaustive list):

* Concatenating a unique, user-defined server name with the tool name, e.g. `web1___search_web` and `web2___search_web`. This strategy may be preferable when unique server names are already provided by the user in a configuration file.
* Generating a random prefix for the tool name, e.g. `jrwxs___search_web` and `6cq52___search_web`. This strategy may be preferable in server proxies where user-defined unique names are not available.
* Using the server URI as a prefix for the tool name, e.g. `web1.example.com:search_web` and `web2.example.com:search_web`. This strategy may be suitable when working with remote MCP servers.

Note that the server-provided name from the initialization flow is not guaranteed to be unique and is not generally suitable for disambiguation purposes.

## Security considerations

When exposing tools:

### Input validation

* Validate all parameters against the schema
* Sanitize file paths and system commands
* Validate URLs and external identifiers
* Check parameter sizes and ranges
* Prevent command injection

### Access control

* Implement authentication where needed
* Use appropriate authorization checks
* Audit tool usage
* Rate limit requests
* Monitor for abuse

### Error handling

* Don't expose internal errors to clients
* Log security-relevant errors
* Handle timeouts appropriately
* Clean up resources after errors
* Validate return values

## Tool discovery and updates

MCP supports dynamic tool discovery:

1. Clients can list available tools at any time
2. Servers can notify clients when tools change using `notifications/tools/list_changed`
3. Tools can be added or removed during runtime
4. Tool definitions can be updated (though this should be done carefully)

## Error handling

Tool errors should be reported within the result object, not as MCP protocol-level errors. This allows the LLM to see and potentially handle the error. When a tool encounters an error:

1. Set `isError` to `true` in the result
2. Include error details in the `content` array

Here's an example of proper error handling for tools:

With FastMCP, raise `ToolError` for tool-level errors (the framework handles `isError` automatically):

```python
from mcp.server.fastmcp import FastMCP

@mcp.tool(name="service_operation", annotations=_WRITE_ANNOTATIONS)
async def service_operation(param: str) -> str:
    """Perform an operation on the service."""
    try:
        result = await perform_operation(param)
        return f"Operation successful: {result}"
    except ExternalAPIError as e:
        raise ToolError(f"API call failed: {e}. Action: Check connectivity and retry.")
    except ValueError as e:
        raise ToolError(f"Invalid input: {e}. Action: Verify parameter format.")
```

This approach allows the LLM to see that an error occurred and potentially take corrective action or request human intervention. Always include a recovery `Action:` in error messages.

## Tool annotations

Tool annotations provide additional metadata about a tool's behavior, helping clients understand how to present and manage tools. These annotations are hints that describe the nature and impact of a tool, but should not be relied upon for security decisions.

### Purpose of tool annotations

Tool annotations serve several key purposes:

1. Provide UX-specific information without affecting model context
2. Help clients categorize and present tools appropriately
3. Convey information about a tool's potential side effects
4. Assist in developing intuitive interfaces for tool approval

### Available tool annotations

The MCP specification defines the following annotations for tools:

| Annotation        | Type    | Default | Description                                                                                                                          |
| ----------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `title`           | string  | -       | A human-readable title for the tool, useful for UI display                                                                           |
| `readOnlyHint`    | boolean | false   | If true, indicates the tool does not modify its environment                                                                          |
| `destructiveHint` | boolean | true    | If true, the tool may perform destructive updates (only meaningful when `readOnlyHint` is false)                                     |
| `idempotentHint`  | boolean | false   | If true, calling the tool repeatedly with the same arguments has no additional effect (only meaningful when `readOnlyHint` is false) |
| `openWorldHint`   | boolean | true    | If true, the tool may interact with an "open world" of external entities                                                             |

### Example usage

Here's how to define tools with annotations for different scenarios:

```python
from mcp.types import ToolAnnotations

# Read-only search tool
_SEARCH_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False,
    idempotentHint=True, openWorldHint=True
)

# Destructive operation tool
_DESTRUCTIVE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True,
    idempotentHint=True, openWorldHint=False
)

# Non-destructive write tool
_WRITE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False,
    idempotentHint=False, openWorldHint=False
)

@mcp.tool(name="service_search", annotations=_SEARCH_ANNOTATIONS)
async def service_search(query: str) -> str:
    """Search for information in the service."""
    ...

@mcp.tool(name="service_delete_record", annotations=_DESTRUCTIVE_ANNOTATIONS)
async def service_delete_record(record_id: str) -> str:
    """Delete a record from the service. This action cannot be undone."""
    ...

@mcp.tool(name="service_create_record", annotations=_WRITE_ANNOTATIONS)
async def service_create_record(table: str, data: dict) -> str:
    """Create a new record in the specified table."""
    ...
```

### Integrating annotations in server implementation

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("example_mcp")

# Define shared annotation sets for consistency
_READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False,
    idempotentHint=True, openWorldHint=False
)

@mcp.tool(name="example_calculate_sum", annotations=_READ_ONLY)
async def example_calculate_sum(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number to add
        b: Second number to add
    """
    return str(a + b)
```

### Best practices for tool annotations

1. **Be accurate about side effects**: Clearly indicate whether a tool modifies its environment and whether those modifications are destructive.

2. **Use descriptive titles**: Provide human-friendly titles that clearly describe the tool's purpose.

3. **Indicate idempotency properly**: Mark tools as idempotent only if repeated calls with the same arguments truly have no additional effect.

4. **Set appropriate open/closed world hints**: Indicate whether a tool interacts with a closed system (like a database) or an open system (like the web).

5. **Remember annotations are hints**: All properties in ToolAnnotations are hints and not guaranteed to provide a faithful description of tool behavior. Clients should never make security-critical decisions based solely on annotations.

## Testing tools

A comprehensive testing strategy for MCP tools should cover:

* **Functional testing**: Verify tools execute correctly with valid inputs and handle invalid inputs appropriately
* **Integration testing**: Test tool interaction with external systems using both real and mocked dependencies
* **Security testing**: Validate authentication, authorization, input sanitization, and rate limiting
* **Performance testing**: Check behavior under load, timeout handling, and resource cleanup
* **Error handling**: Ensure tools properly report errors through the MCP protocol and clean up resources

**Critical**: Do NOT rely on manually chatting with an LLM to validate your MCP server ("vibe testing"). LLM interactions are stochastic, slow, expensive, and opaque. Write deterministic, automated tests. Use the evaluation harness for end-to-end testing.

### Testing Progression
1. Unit tests for each tool handler (mocked dependencies)
2. Protocol compliance tests (initialization, capability negotiation)
3. Error handling tests (invalid inputs, missing params, server failures)
4. Security tests (injection, traversal, unauthorized access)
5. Integration tests against real services (marked with `@pytest.mark.integration`)

### FastMCP In-Memory Testing (Python)

FastMCP supports direct in-memory testing without subprocess management:

```python
from fastmcp import Client

@pytest.fixture
async def mcp_client():
    async with Client(transport=mcp) as client:
        yield client

async def test_tool(mcp_client):
    result = await mcp_client.call_tool("tool_name", {"param": "value"})
    assert len(result) > 0
    assert result[0].type == "text"
```

---

## 15. Structured Output (New in 2025)

The MCP specification now supports structured tool output via `outputSchema` and `structuredContent`:

### How It Works
- Define `outputSchema` (JSON Schema) on tool registration to declare the structure of returned data
- Return both `content` (unstructured text, backward-compatible) and `structuredContent` (typed JSON)
- Servers MUST ensure `structuredContent` conforms to the declared `outputSchema`

### When to Use
- Tools that return structured data (lists, objects, metrics)
- When downstream consumers need typed data
- For tools used in automated pipelines

### Example
```python
@mcp.tool(
    name="service_get_metrics",
    output_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "items": {"type": "array", "items": {"type": "object"}}
        }
    }
)
async def get_metrics(query: str) -> dict:
    results = await fetch_metrics(query)
    return {"count": len(results), "items": results}
```

---

## 16. Anti-Patterns to Avoid

These are common mistakes that lead to poor MCP server quality:

1. **Vibe testing** — Relying on LLM chat instead of deterministic automated tests
2. **God servers** — One MCP server that does everything; prefer single-responsibility servers
3. **Token passthrough** — Passing client tokens directly to downstream APIs without validation
4. **Hardcoded credentials** — Embedding secrets in code or config files
5. **Missing input validation** — Trusting LLM-generated tool arguments without schema validation
6. **Wildcard scopes** — Granting `*` or `full-access` permissions
7. **No observability** — Skipping metrics, logging, and tracing
8. **Ignoring tool annotations** — Not declaring `readOnlyHint`/`destructiveHint` when applicable
9. **Blocking operations** — Synchronous calls that freeze an async server; use async throughout
10. **Session as authentication** — Using session IDs as the sole auth mechanism
11. **Writing to stdout** — Debug output on stdio transport breaks the JSON-RPC protocol
12. **No rate limiting** — Allowing unlimited tool invocations, enabling abuse or runaway loops
13. **Wrapping APIs 1:1** — Directly exposing every API endpoint instead of building workflow-oriented tools
14. **Returning excessive data** — Not respecting agent context budgets; return high-signal information
15. **Fragile error detection** — Using string pattern matching on error messages instead of error codes
16. **Silent config fallbacks** — Falling back to defaults without logging warnings when config fails to load

---

## 17. Observability and Logging

### MCP Built-in Logging

The protocol supports a `logging` capability. Servers can send structured log messages to clients:

```python
@mcp.tool()
async def my_tool(param: str, ctx: Context) -> str:
    await ctx.info(f"Processing: {param}")
    await ctx.debug("Detailed trace info")
    await ctx.warning("Something unusual happened")
```

### Production Observability

- **Structured logging**: Use JSON-formatted logs with correlation IDs, tool name, latency, customer ID
- **Audit trail**: Log every tool invocation with correlation ID for traceability
- **Metrics**: Track request count, duration (P50/P95/P99), error rate per tool
- **Health checks**: Implement health endpoints classifying status as healthy/degraded/unhealthy
- **Never log sensitive data**: Sanitize PII, credentials, and query content from logs

### Correlation ID Pattern

Generate a correlation ID for each tool invocation and propagate it through all downstream calls:

```python
import uuid

def generate_correlation_id() -> str:
    return uuid.uuid4().hex[:8]

@contextmanager
def audit_tool_call(tool_name: str, correlation_id: str, customer_id: str):
    start = time.time()
    try:
        yield
        logger.info("tool_call", extra={
            "tool": tool_name, "cid": correlation_id,
            "customer": customer_id, "latency_ms": (time.time() - start) * 1000,
            "success": True
        })
    except Exception:
        logger.error("tool_call_failed", extra={
            "tool": tool_name, "cid": correlation_id,
            "customer": customer_id, "latency_ms": (time.time() - start) * 1000,
            "success": False
        })
        raise
```

---

## 18. Brain Bridge Internal Standards

> **Note:** This section contains organization-specific conventions for Brain Bridge MCP servers. If you're building MCP servers outside Brain Bridge, treat these as sensible defaults you can adapt to your own project conventions.

### Project Naming

Use `bb-mcp-{service}` for repo names and `{service}_mcp` for Python packages. Consistent naming across the org makes it easy to find and manage MCP servers — when someone sees `bb-mcp-slack`, they immediately know what it is.

### Project Structure (Python)

This structure separates concerns so that core tool logic is reusable across transport layers (FastMCP for containers, Lambda for gateway targets). Without this separation, you end up duplicating business logic.

```
bb-mcp-{service}/
├── src/{service}_mcp/
│   ├── __init__.py
│   ├── server.py              # FastMCP server, tool decorators
│   ├── lambda_handler.py      # Optional: only for Gateway Lambda targets
│   ├── core/
│   │   ├── tools.py           # Transport-agnostic tool implementations
│   │   ├── state.py           # AppState management (if stateful)
│   │   └── audit.py           # Structured audit logging
│   ├── aws/                   # AWS service integrations (if applicable)
│   ├── tools/                 # Tool input validation (Pydantic models)
│   ├── config/
│   │   ├── models.py          # Pydantic config models
│   │   └── loader.py          # Config loading (S3, env, files)
│   └── resources/             # MCP resource endpoints
├── cdk/                       # CDK infrastructure (if deployed to AWS)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
├── Dockerfile
├── deploy.sh
├── .mcp.json
└── README.md
```

### Architecture Principles

1. **Separation of concerns**: Core tool logic in `core/tools.py` stays transport-agnostic — if it imports FastMCP or Lambda-specific code, it can't be reused across deployment targets
2. **Metadata-first**: Pre-load context on startup to reduce per-request latency and token usage
3. **Defense-in-depth security**: Multi-layer input validation (schema → business rules → allowlists) because LLM-generated inputs are unpredictable
4. **Explicit error recovery**: Every error message includes a suggested next action — agents can't fix what they can't diagnose
5. **Audit everything**: Correlation IDs on all tool invocations with structured JSON logging, so you can trace a failure back through the call chain

### Configuration

These tool configurations keep code consistent across our MCP servers and catch common issues early:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true    # Catches type errors that surface as runtime bugs in production

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: requires AWS services", "agentcore: requires AgentCore"]

[tool.bandit]
exclude_dirs = ["tests", "cdk.out"]
```

### Tool Naming Convention

Use the pattern `{service}_{verb}_{noun}` or `{service}_{verb}` — the service prefix prevents name collisions when multiple MCP servers are used together (which is the common case). Examples: `datalake_run_query`, `airtable_search_records`.

### Error Handling Pattern

Implement these patterns because agents interact with tools differently than humans — they need structured, actionable feedback to self-correct:

1. **Custom exception hierarchy**: Separate permanent errors from transient/retryable ones so agents know whether to retry
2. **Retry with backoff**: Use `tenacity` for transient errors (3 attempts, exponential backoff 1-4s) — network calls to external APIs will occasionally fail
3. **Actionable messages**: Include the error, context, and suggested recovery action — "User not found: 'jon'. Did you mean 'john_doe' or 'jon_smith'?" is far more useful than "404 Not Found"
4. **Fuzzy matching**: When entities aren't found, suggest similar names — agents make typos just like humans

### Tool Annotations

Declare annotations on every tool — they help clients build appropriate approval UIs and categorize tool behavior. An agent client can auto-approve read-only tools but prompt the user for destructive ones. See [Tool Annotations](#tool-annotations) above for the full reference.

### Testing

- Unit tests with mocked dependencies (no AWS calls in CI)
- Integration tests marked with `@pytest.mark.integration`
- FastMCP in-memory testing using `Client(transport=mcp)` — no subprocess overhead
- Quality gates: `ruff check`, `ruff format`, `mypy --strict`, `bandit -r src/`, `pytest --cov`
- Target 90%+ unit test coverage — this is about catching regressions, not hitting a number. See [Python Guide: Quality Checklist](./python_mcp_server.md#quality-checklist) for the full checklist
