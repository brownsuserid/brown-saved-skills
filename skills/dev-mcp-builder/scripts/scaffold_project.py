"""Scaffold a new MCP server project with the standard directory structure.

Usage:
    python scripts/scaffold_project.py <service-name> [--output-dir <path>]

Examples:
    python scripts/scaffold_project.py slack
    python scripts/scaffold_project.py github --output-dir /tmp
"""

import argparse
import sys
from pathlib import Path

PYPROJECT_TEMPLATE = """[project]
name = "{service_mcp}"
version = "0.1.0"
description = "MCP server for {service_title}"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "mypy>=1.13",
    "bandit>=1.8",
]
cdk = [
    "aws-cdk-lib>=2.170.0",
    "constructs>=10.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["integration: requires AWS services", "agentcore: requires AgentCore"]

[tool.bandit]
exclude_dirs = ["tests", "cdk.out"]
"""

SERVER_TEMPLATE = '''"""FastMCP server for {service_title}."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("{service_mcp}")

# Shared annotation sets
_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


@mcp.tool(name="{service}_hello", annotations=_READ_ONLY)
async def hello(name: str = "world") -> str:
    """Say hello. Replace this with your first real tool.

    Args:
        name: Who to greet (default: "world")
    """
    return f"Hello, {{name}}! {service_title} MCP server is running."


if __name__ == "__main__":
    mcp.run()
'''

INIT_TEMPLATE = '''"""{service_title} MCP Server."""
'''

CORE_TOOLS_TEMPLATE = '''"""Transport-agnostic tool implementations.

Keep business logic here so it can be reused by both
the FastMCP server (async) and Lambda handler (sync).
"""


def hello(name: str = "world") -> str:
    """Example tool implementation."""
    return f"Hello, {{name}}!"
'''

STATE_TEMPLATE = '''"""Application state management."""

from dataclasses import dataclass, field


@dataclass
class AppState:
    """Shared state initialized once on startup.

    Use lazy initialization for expensive resources
    (API clients, database connections, etc.).
    """

    _initialized: bool = field(default=False, repr=False)

    def initialize(self) -> None:
        """Initialize resources. Call once on startup."""
        if self._initialized:
            return
        # Add initialization logic here
        self._initialized = True
'''

AUDIT_TEMPLATE = '''"""Structured audit logging with correlation IDs."""

import logging
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """Generate a short correlation ID for request tracing."""
    return uuid.uuid4().hex[:8]


@contextmanager
def audit_tool_call(
    tool_name: str, correlation_id: str, customer_id: str = "unknown"
) -> Generator[None, None, None]:
    """Context manager for auditing tool invocations."""
    start = time.time()
    try:
        yield
        logger.info(
            "tool_call",
            extra={{
                "tool": tool_name,
                "cid": correlation_id,
                "customer": customer_id,
                "latency_ms": (time.time() - start) * 1000,
                "success": True,
            }},
        )
    except Exception:
        logger.error(
            "tool_call_failed",
            extra={{
                "tool": tool_name,
                "cid": correlation_id,
                "customer": customer_id,
                "latency_ms": (time.time() - start) * 1000,
                "success": False,
            }},
        )
        raise
'''

CONFTEST_TEMPLATE = '''"""Shared test fixtures."""

import pytest
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def mcp_server() -> FastMCP:
    """Provide the MCP server instance for testing."""
    from {service_mcp}.server import mcp

    return mcp
'''

TEST_EXAMPLE_TEMPLATE = '''"""Example unit tests for {service_title} MCP server."""

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_hello_tool(mcp_server):
    """Test the hello tool returns a greeting."""
    async with Client(transport=mcp_server) as client:
        result = await client.call_tool("{service}_hello", {{"name": "test"}})
        assert len(result) > 0
        assert "Hello, test" in result[0].text


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test that tools are discoverable."""
    async with Client(transport=mcp_server) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "{service}_hello" in tool_names
'''

MCP_JSON_TEMPLATE = """{{
  "mcpServers": {{
    "{service_mcp}": {{
      "command": "uv",
      "args": ["run", "python", "-m", "{service_mcp}.server"]
    }}
  }}
}}
"""

README_TEMPLATE = """# bb-mcp-{service}

MCP server for {service_title}.

## Development

```bash
uv sync --all-extras
uv run python -m {service_mcp}.server   # Run locally (stdio)
```

## Testing

```bash
uv run pytest -m "not integration"
uv run ruff check . && uv run mypy src/ && uv run bandit -r src/
uv run pytest --cov --cov-report=html
```

## Deployment

See the [MCP Builder skill](../dev-mcp-builder/SKILL.md) Phase 4 for deployment instructions.
"""

DOCKERFILE_TEMPLATE = """FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

EXPOSE 8000

CMD ["python", "-m", "{service_mcp}.server"]
"""


def scaffold(service: str, output_dir: Path) -> Path:
    """Create a new MCP server project."""
    service_mcp = f"{service}_mcp"
    service_title = service.replace("-", " ").replace("_", " ").title()
    project_dir = output_dir / f"bb-mcp-{service}"

    if project_dir.exists():
        print(f"Error: {project_dir} already exists")
        sys.exit(1)

    fmt = {"service": service, "service_mcp": service_mcp, "service_title": service_title}

    # Create directory structure
    dirs = [
        f"src/{service_mcp}/core",
        f"src/{service_mcp}/aws",
        f"src/{service_mcp}/tools",
        f"src/{service_mcp}/config",
        f"src/{service_mcp}/resources",
        "cdk/constructs",
        "tests/unit",
        "tests/integration",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    # Write files
    files = {
        "pyproject.toml": PYPROJECT_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/__init__.py": INIT_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/server.py": SERVER_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/core/__init__.py": "",
        f"src/{service_mcp}/core/tools.py": CORE_TOOLS_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/core/state.py": STATE_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/core/audit.py": AUDIT_TEMPLATE.format(**fmt),
        f"src/{service_mcp}/aws/__init__.py": "",
        f"src/{service_mcp}/tools/__init__.py": "",
        f"src/{service_mcp}/config/__init__.py": "",
        f"src/{service_mcp}/config/models.py": "",
        f"src/{service_mcp}/config/loader.py": "",
        f"src/{service_mcp}/resources/__init__.py": "",
        "tests/__init__.py": "",
        "tests/conftest.py": CONFTEST_TEMPLATE.format(**fmt),
        "tests/unit/__init__.py": "",
        "tests/unit/test_tools.py": TEST_EXAMPLE_TEMPLATE.format(**fmt),
        "tests/integration/__init__.py": "",
        "cdk/__init__.py": "",
        "cdk/constructs/__init__.py": "",
        ".mcp.json": MCP_JSON_TEMPLATE.format(**fmt),
        "README.md": README_TEMPLATE.format(**fmt),
        "Dockerfile": DOCKERFILE_TEMPLATE.format(**fmt),
    }

    for path, content in files.items():
        filepath = project_dir / path
        filepath.write_text(content)

    return project_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new MCP server project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python scaffold_project.py slack",
    )
    parser.add_argument(
        "service",
        help="Service name (e.g., 'slack', 'github', 'jira')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Parent directory for the new project (default: current directory)",
    )

    args = parser.parse_args()

    # Validate service name
    service = args.service.lower().replace("-", "_")
    if not service.isidentifier():
        print(f"Error: '{args.service}' is not a valid Python identifier")
        sys.exit(1)

    project_dir = scaffold(service, args.output_dir)
    print(f"Created MCP server project: {project_dir}")
    print("\nNext steps:")
    print(f"  cd {project_dir}")
    print("  uv sync --all-extras")
    print(f"  uv run python -m {service}_mcp.server")


if __name__ == "__main__":
    main()
