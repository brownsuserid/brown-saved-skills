---
name: dev-mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers in Python using FastMCP, deployed to AWS via AgentCore Runtime (container) or Gateway (Lambda). Use this skill whenever the user wants to build an MCP server, create MCP tools, wrap an API or external service for AI agents, deploy MCP servers to AWS AgentCore, write FastMCP code, or integrate external services via Model Context Protocol. Also triggers when code imports FastMCP, references mcp.server, or the user mentions tool servers for AI agents — even if they don't explicitly say "MCP".
license: Complete terms in LICENSE.txt
---

# MCP Server Development Guide

## Overview

To create high-quality MCP (Model Context Protocol) servers that enable LLMs to effectively interact with external services, use this skill. An MCP server provides tools that allow LLMs to access external services and APIs. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks using the tools provided.

**MCP Spec Version**: Based on protocol revisions 2025-03-26 and 2025-06-18.
**Key changes since 2024**: Streamable HTTP replaces SSE transport, structured output via `outputSchema`, tool `title` field, session management, elicitation support.
**Stack**: Python 3.12+ / FastMCP / Pydantic v2 / CDK / AgentCore Runtime (container) or Gateway (Lambda)

---

# Process

## High-Level Workflow

Creating a high-quality MCP server involves five main phases:

### Phase 1: Deep Research and Planning

#### 1.1 Understand Agent-Centric Design Principles

The most common mistake when building MCP servers is wrapping each API endpoint as a separate tool. This forces agents to make multiple tool calls for a single task and wastes context on orchestrating API calls instead of solving the user's problem.

**Design Workflow Tools, Not API Wrappers:**

Instead of mirroring the API's structure, design tools around what the agent actually needs to accomplish. Ask: "What question is the user asking?" — then build one tool that answers it.

Bad example (weather API wrapper — 3 tool calls to answer "What's the weather in Tokyo?"):
- `get_current_weather(city)` → current conditions
- `get_forecast(city, days)` → future forecast
- `get_weather_alerts(city)` → active alerts

Good example (workflow tool — 1 tool call):
- `get_weather(city, timeframe="now|today|week", include_alerts=True)` → returns current conditions OR forecast based on timeframe, automatically includes relevant alerts. One call gives the agent everything it needs.

The same principle applies everywhere: a `search_jira` tool that returns issues with their comments and linked PRs is far more useful than separate `search_issues`, `get_comments`, and `get_linked_prs` tools. Think about what information travels together in real workflows.

**Optimize for Limited Context:**
- Agents have constrained context windows — make every token count
- Return high-signal information, not exhaustive data dumps
- Provide "concise" vs "detailed" response format options
- Default to human-readable identifiers over technical codes (names over IDs)

**Design Actionable Error Messages:**
- Error messages should guide agents toward correct usage: "Try using filter='active_only' to reduce results"
- Make errors educational, not just diagnostic

**Use All MCP Primitives, Not Just Tools:**

MCP servers can expose resources (read-only data), prompts (reusable templates), and tools (actions). Most servers only implement tools, missing opportunities:
- **Resources** (`@mcp.resource`): Expose reference data agents need repeatedly — API schemas, configuration, lookup tables. Resources are loaded into context without a tool call, reducing round-trips.
- **Prompts** (`@mcp.prompt`): Provide reusable prompt templates for common workflows — "analyze this Jira sprint", "summarize weather for a trip". Prompts help agents use your tools effectively.
- **Tools** (`@mcp.tool`): Actions that do work — queries, mutations, computations.

Think about which parts of your API are better as resources (data the agent reads) vs tools (actions the agent takes).

**Use Evaluation-Driven Development:**
- Create realistic evaluation scenarios early
- Let agent feedback drive tool improvements
- Prototype quickly and iterate based on actual agent performance

#### 1.2 Study MCP Protocol Documentation

**Fetch the latest MCP protocol documentation:**

Use WebFetch to load: `https://modelcontextprotocol.io/llms-full.txt`

This comprehensive document contains the complete MCP specification and guidelines.

#### 1.3 Study Framework Documentation

**Load and read the following reference files:**

- **MCP Best Practices**: [View Best Practices](./reference/mcp_best_practices.md) - Core guidelines for all MCP servers
- **Python SDK Documentation**: Use WebFetch to load `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [Python Implementation Guide](./reference/python_mcp_server.md) - Python-specific best practices, patterns, and examples

#### 1.4 Exhaustively Study API Documentation

To integrate a service, read through **ALL** available API documentation:
- Official API reference documentation
- Authentication and authorization requirements
- Rate limiting and pagination patterns
- Error responses and status codes
- Available endpoints and their parameters
- Data models and schemas

**To gather comprehensive information, use web search and the WebFetch tool as needed.**

#### 1.5 Create a Comprehensive Implementation Plan

Based on your research, create a detailed plan that includes:

**Tool Selection (Workflow-First):**
- Identify the top 5-10 workflows agents need to accomplish (not API endpoints to wrap)
- For each workflow, design one tool that completes the task in a single call
- Consolidate related API calls into unified tools with parameters that control scope
- Only split into multiple tools when operations are genuinely independent

**Resources and Prompts:**
- Identify reference data that agents need repeatedly (schemas, configs, lookup tables) — expose as MCP resources
- Design prompt templates for common workflows — these help agents use your tools effectively
- Resources reduce tool call round-trips; prompts standardize complex multi-tool workflows

**Shared Utilities and Helpers:**
- Identify common API request patterns
- Plan pagination helpers
- Design filtering and formatting utilities
- Plan error handling strategies (permanent vs transient errors, retry logic)

**Input/Output Design:**
- Define input validation models (Pydantic BaseModel with Field constraints)
- Design consistent response formats (JSON and Markdown), and configurable detail levels
- Plan for large-scale usage (thousands of users/resources)
- Implement character limits and truncation strategies (e.g., 25,000 tokens)

**Error Handling Strategy:**
- Plan graceful failure modes with custom exception hierarchy
- Design clear, actionable, LLM-friendly error messages that suggest recovery actions
- Consider rate limiting and timeout scenarios with retry logic
- Handle authentication and authorization errors

**Deployment Architecture:**
- Plan for dual-transport: stdio (local dev) and Streamable HTTP (AgentCore Runtime) or Lambda (Gateway)
- Ensure core tool logic is transport-agnostic in `core/tools.py`
- Choose deployment path: AgentCore Runtime (container, primary) or Gateway Lambda targets (secondary)
- Plan CDK infrastructure accordingly (CfnRuntime + ECR, or Lambda + CfnGatewayTarget)

---

### Phase 2: Implementation

Now that you have a comprehensive plan, begin implementation.

#### 2.1 Set Up Project Structure

All shared MCP servers should be published to the **`bb-mcp`** monorepo — this is the central repository for Brain Bridge MCP servers. Scaffold new servers there so they benefit from shared CI/CD, consistent structure, and team discoverability.

Set up the project following the standard structure in [MCP Best Practices](./reference/mcp_best_practices.md#18-brain-bridge-internal-standards). The key architectural idea: keep core tool logic in `core/tools.py` as transport-agnostic functions so they work in both FastMCP (async) and Lambda (sync) contexts. This avoids duplicating business logic across transport layers.

Use the scaffolding script to generate the boilerplate:
```bash
python scripts/scaffold_project.py {service-name}
```

#### 2.2 Implement Core Infrastructure First

Build shared utilities before individual tools — this prevents every tool from reinventing pagination, error handling, and API request patterns. See [Python Guide: Shared Utilities](./reference/python_mcp_server.md#shared-utilities) for code examples. Key pieces:
- API request helpers with retry logic (`tenacity` for transient errors)
- Response formatters (JSON and Markdown) — agents need both: Markdown for human-readable output, JSON for programmatic chaining
- Pagination helpers — agents have limited context, so returning unbounded lists wastes their budget
- Custom exception hierarchy — separating permanent from transient errors lets agents decide whether to retry
- State management (AppState dataclass with lazy initialization)

#### 2.3 Implement Tools Systematically

For each tool in the plan, load the [Python Implementation Guide](./reference/python_mcp_server.md) and follow its patterns for:
- **Input schemas**: Pydantic BaseModel with Field constraints and descriptive examples
- **Docstrings**: These become the tool's description that agents see — make them thorough with usage examples and error documentation
- **Tool logic**: Core in `core/tools.py`, FastMCP wrapper in `server.py`, optional Lambda wrapper
- **Tool annotations**: Every tool needs `ToolAnnotations` from `mcp.types` — these help clients categorize tools and build appropriate approval UIs. See [MCP Best Practices: Tool Annotations](./reference/mcp_best_practices.md#tool-annotations) for the full annotation reference

#### 2.4 Implement Resources and Prompts

Don't stop at tools — use all MCP primitives:

**Resources** — Expose read-only reference data agents frequently need:
```python
@mcp.resource("config://api-schema")
async def get_api_schema() -> str:
    """Available API fields and their types."""
    return json.dumps(API_SCHEMA)

@mcp.resource("data://projects/{project_key}")
async def get_project_info(project_key: str) -> str:
    """Project metadata (members, settings, workflows)."""
    return json.dumps(await fetch_project(project_key))
```

**Prompts** — Provide reusable templates for common workflows:
```python
@mcp.prompt()
async def analyze_sprint(project: str, sprint: str) -> str:
    """Analyze a sprint's health and progress."""
    return f"Use the search tool to find all issues in {project} sprint {sprint}, then summarize progress, blockers, and risks."
```

Resources and prompts live in `src/{service_mcp}/resources/` and are registered in `server.py`.

#### 2.5 Configure for AgentCore Deployment

Choose the appropriate deployment path:

**Primary: AgentCore Runtime (Container)** — Add `stateless_http=True` to FastMCP constructor and create a Dockerfile exposing `0.0.0.0:8000/mcp`. AgentCore Runtime manages sessions, so the server stays stateless per-request.

**Secondary: Gateway Lambda Targets** — Only for exposing existing Lambda functions as MCP tools. See [Python Guide: Lambda Handler](./reference/python_mcp_server.md#lambda-handler-for-agentcore-gateway-optional) for the pattern.

#### 2.6 Follow Python Best Practices

Load the [Python Implementation Guide](./reference/python_mcp_server.md) for detailed patterns covering FastMCP registration, Pydantic v2 models, async/await, type hints (`mypy --strict`), and module-level constants.

---

### Phase 3: Review and Refine

#### 3.1 Code Quality Review

Check that the implementation follows DRY principles (no duplicated logic between tools), transport agnosticism (core logic works in both FastMCP and Lambda), and consistent error handling with recovery guidance.

#### 3.2 Test and Build

Write deterministic, automated tests — don't rely on chatting with an LLM to validate ("vibe testing"). LLM interactions are stochastic, slow, and opaque. See [Python Guide: Automated Testing](./reference/python_mcp_server.md#automated-testing) for FastMCP in-memory testing patterns.

```bash
uv run pytest -m "not integration"                    # Unit tests
uv run ruff check . && uv run mypy src/ && uv run bandit -r src/  # Quality gates
uv run pytest --cov --cov-report=html                 # Coverage
```

#### 3.3 Use Quality Checklist

Verify implementation using the checklist in [Python Guide: Quality Checklist](./reference/python_mcp_server.md#quality-checklist).

---

### Phase 4: Deploy to AWS AgentCore

After implementation and testing, deploy to AWS. Choose the appropriate deployment path.

#### 4.1 Quickstart: AgentCore Starter Toolkit (No CDK Required)

The simplest deployment path uses the `bedrock-agentcore-starter-toolkit` CLI:

```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure    # Set up AWS credentials and region
agentcore deploy       # Deploy MCP server container to AgentCore Runtime
agentcore invoke       # Test the deployed server
agentcore destroy      # Clean up resources
```

This handles ECR, CodeBuild, and CfnRuntime creation automatically without CDK.

> **Region**: All Brain Bridge deployments target `us-east-1` by default. See `dev-shared-references/aws-standards.md` for details.

#### 4.2 Primary Path: AgentCore Runtime (Container via CDK)

Deploy the FastMCP server as a Docker container to AgentCore Runtime:

1. **Server Configuration**: Ensure `stateless_http=True` on FastMCP constructor
2. **Dockerfile**: Expose `0.0.0.0:8000/mcp` endpoint
3. **ECR Repository**: Store the container image
4. **CodeBuild**: Build and push the Docker image
5. **CfnRuntime**: Register the container with AgentCore Runtime
6. **IAM Role**: Multi-principal trust (AgentCore, Bedrock, ECS) with least-privilege permissions
7. **CloudWatch**: Log groups with metrics and error filters

See [Python Guide](./reference/python_mcp_server.md) for CDK CfnRuntime patterns.

#### 4.3 Secondary Path: Gateway Lambda Targets (via CDK)

For exposing existing Lambda functions as MCP tools via AgentCore Gateway:

1. **Lambda Function**: Python 3.12, handler pointing to `lambda_handler.handler`
2. **Gateway Target**: Registers Lambda as an AgentCore Gateway target with tool schemas
3. **Tool schemas**: Declared in CDK (inputSchema for each tool)
4. **Credential provider**: `GATEWAY_IAM_ROLE` (IAM-based, not OAuth)
5. **Gateway invocation**: Lambda receives tool name in `context.client_context.custom`

See [Python Guide](./reference/python_mcp_server.md) for CDK CfnGatewayTarget patterns.

#### 4.4 Deployment

Use the standard `deploy.sh` pattern:
- Pre-flight: validate AWS profile, check CDK bootstrap
- Parallel execution: CDK deploy + Docker build/push
- Post-deployment: extract outputs, display summary
- Auto-detect gateway: `aws bedrock-agentcore-control list-gateways`

---

### Phase 5: Create Evaluations

After deploying your MCP server, create comprehensive evaluations to test its effectiveness.

**Load [Evaluation Guide](./reference/evaluation.md) for complete evaluation guidelines.**

#### 5.1 Understand Evaluation Purpose

Evaluations test whether LLMs can effectively use your MCP server to answer realistic, complex questions.

#### 5.2 Create 10 Evaluation Questions

Follow the process outlined in the evaluation guide:

1. **Tool Inspection**: List available tools and understand their capabilities
2. **Content Exploration**: Use READ-ONLY operations to explore available data
3. **Question Generation**: Create 10 complex, realistic questions
4. **Answer Verification**: Solve each question yourself to verify answers

#### 5.3 Evaluation Requirements

Each question must be:
- **Independent**: Not dependent on other questions
- **Read-only**: Only non-destructive operations required
- **Complex**: Requiring multiple tool calls and deep exploration
- **Realistic**: Based on real use cases humans would care about
- **Verifiable**: Single, clear answer that can be verified by string comparison
- **Stable**: Answer won't change over time

#### 5.4 Output Format

Create an XML file with this structure:

```xml
<evaluation>
  <qa_pair>
    <question>Find discussions about AI model launches with animal codenames. One model needed a specific safety designation that uses the format ASL-X. What number X was being determined for the model named after a spotted wild cat?</question>
    <answer>3</answer>
  </qa_pair>
<!-- More qa_pairs... -->
</evaluation>
```

---

# Reference Files

## Documentation Library

Load these resources as needed during development:

### Core MCP Documentation (Load First)
- **MCP Protocol**: Fetch from `https://modelcontextprotocol.io/llms-full.txt` - Complete MCP specification
- [MCP Best Practices](./reference/mcp_best_practices.md) - Universal MCP guidelines including:
  - Server and tool naming conventions
  - Response format guidelines (JSON vs Markdown)
  - Pagination best practices
  - Character limits and truncation strategies
  - Tool development guidelines
  - Security and error handling standards
  - Structured output (outputSchema)
  - Anti-patterns to avoid
  - Observability and logging
  - Brain Bridge internal standards for consistency

### SDK Documentation (Load During Phase 1/2)
- **Python SDK**: Fetch from `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`

### Implementation Guide (Load During Phase 2)
- [Python Implementation Guide](./reference/python_mcp_server.md) - Complete Python/FastMCP guide with:
  - Server initialization patterns
  - Pydantic model examples
  - Tool registration with `@mcp.tool` and `ToolAnnotations`
  - State management (AppState pattern)
  - Custom exception hierarchy with retry logic
  - Separation of concerns (transport-agnostic core tools)
  - Lambda handler for AgentCore Gateway
  - CDK infrastructure patterns
  - FastMCP in-memory testing
  - Complete working examples
  - Quality checklist

### Evaluation Guide (Load During Phase 5)
- [Evaluation Guide](./reference/evaluation.md) - Complete evaluation creation guide with:
  - Question creation guidelines
  - Answer verification strategies
  - XML format specifications
  - Example questions and answers
  - Running an evaluation with the provided scripts
