# Python Coding Standards

This file contains the Python coding standards and best practices to be applied during feature implementation.

## Role & Expertise

- Python master with exceptional coding skills
- Deep understanding of Python's best practices, design patterns, and idioms
- Focus on identifying and preventing potential errors
- Prioritize writing efficient and maintainable code

## Hardware & Environment

- Mac M4 Mini
- Terminal: omz / zsh

## Technology Stack

- **Python Version:** Python 3.13+
- **Dependency Management:** uv
- **Code Formatting:** ruff
- **Type Hinting:** Strictly use the `typing` module. All functions, methods, and class members must have type annotations.
- **Testing Framework:** `pytest`
- **Documentation:** Google style docstring
- **Environment Management:** uv
- **Containerization:** `docker`, `docker-compose`
- **Asynchronous Programming:** Prefer `async` and `await`
- **Web Framework:** `fastapi`
- **LLM Agent Framework:** `Google Agent Development Kit` or `AWS Strands`
- **Data Processing / Data Validation:** `pandas`, `numpy`, `pydantic` (2+)
- **Data Change Management:** `alembic`
- **Version Control:** `git`
- **Server:** `uvicorn` (with `nginx` or `caddy`)
- **Process Management:** `systemd`, `supervisor`
- **Object-Relational Mapping:** `SQLAlchemy`

## Coding Guidelines

### 1. Pythonic Practices

- **Elegance and Readability:** Strive for elegant and Pythonic code that is easy to understand and maintain
- **PEP 8 Compliance:** Adhere to PEP 8 guidelines for code style, with Ruff as the primary linter and formatter
- **Explicit over Implicit:** Favor explicit code that clearly communicates its intent over implicit, overly concise code
- **Zen of Python:** Keep the Zen of Python in mind when making design decisions

### 2. Modular Design

- **Single Responsibility Principle:** Each module/file should have a well-defined, single responsibility
- **Reusable Components:** Develop reusable functions and classes, favoring composition over inheritance
- **Package Structure:** Organize code into logical packages and modules

### 3. Code Quality

#### Comprehensive Type Annotations (MANDATORY)

- All functions, methods, and class members must have type annotations
- Use the most specific types possible
- Use the `typing` module

Example:
```python
from typing import List, Dict, Optional

def process_user(
    user_id: int,
    options: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """Process user data with optional configuration."""
    ...
```

#### Detailed Docstrings (MANDATORY)

- All functions, methods, and classes must have Google-style docstrings
- Thoroughly explain purpose, parameters, return values, and exceptions raised
- Include usage examples where helpful

Example:
```python
def calculate_discount(price: float, discount_rate: float) -> float:
    """Calculate the discounted price.

    Args:
        price: The original price of the item
        discount_rate: The discount rate as a decimal (0.0 to 1.0)

    Returns:
        The final price after applying the discount

    Raises:
        ValueError: If discount_rate is not between 0.0 and 1.0

    Examples:
        >>> calculate_discount(100.0, 0.2)
        80.0
    """
    if not 0.0 <= discount_rate <= 1.0:
        raise ValueError("Discount rate must be between 0.0 and 1.0")
    return price * (1.0 - discount_rate)
```

#### Thorough Unit Testing (MANDATORY)

- Aim for high test coverage (90% or higher) using `pytest`
- Test both common cases and edge cases
- Tag integration tests with `@pytest.mark.integration` so they're skipped by CI/CD

#### Robust Exception Handling

**Rules (in priority order):**

1. **Catch the narrowest exception type possible** — never `except Exception` when a specific type exists
2. **Always re-raise after logging** — unless at a documented boundary (see below)
3. **Never return a default value from a broad `except` block** — this silently swallows errors
4. **Provide informative error messages** — include context about what failed and why
5. **Implement custom exception classes** when domain-specific errors need distinct handling
6. **Never use bare `except:`** — always specify the exception type

**When NOT to re-raise (documented boundaries only):**
- User-facing API boundaries (return HTTP error response instead)
- Cleanup/teardown code (log + continue to clean up remaining resources)
- Graceful degradation where the fallback is explicitly designed and documented

**Examples:**
```python
# ✓ GOOD: Specific exception, re-raises after logging
try:
    result = process_data(user_input)
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise

# ✓ GOOD: Documented boundary — API endpoint returns error response
try:
    result = process_data(user_input)
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    return {"error": str(e)}, 400  # Boundary: user-facing API

# ❌ BAD: Swallows error — caller never knows parsing failed
try:
    config = parse_config(path)
except Exception as e:
    logger.warning(f"Parse failed: {e}")
    return {}  # Silent data loss!

# ❌ BAD: Broad catch hides the real error type
try:
    user = get_user(user_id)
except Exception:
    return None  # Was it NotFound? PermissionDenied? NetworkError?

# ✓ GOOD: Narrow catch, caller can handle different failures
try:
    user = get_user(user_id)
except UserNotFoundError:
    logger.info(f"User {user_id} not found")
    return None
# Let other exceptions propagate — they indicate real problems
```

#### Logging

- Employ the `logging` module judiciously
- Log important events, warnings, and errors
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### 4. Performance Optimization

- **Asynchronous Programming:** Leverage `async` and `await` for I/O-bound operations to maximize concurrency
- **Caching:** Apply `functools.lru_cache`, `@cache` (Python 3.9+), or `fastapi.Depends` caching where appropriate
- **Resource Monitoring:** Use `psutil` or similar to monitor resource usage and identify bottlenecks
- **Memory Efficiency:** Ensure proper release of unused resources to prevent memory leaks
- **Concurrency:** Employ `concurrent.futures` or `asyncio` to manage concurrent tasks effectively
- **Database Best Practices:** Design database schemas efficiently, optimize queries, and use indexes wisely

### 5. API Development with FastAPI

- **Data Validation:** Use Pydantic models for rigorous request and response data validation
- **Dependency Injection:** Effectively use FastAPI's dependency injection for managing dependencies
- **Routing:** Define clear and RESTful API routes using FastAPI's `APIRouter`
- **Background Tasks:** Utilize FastAPI's `BackgroundTasks` or integrate with Celery for background processing
- **Security:** Implement robust authentication and authorization (e.g., OAuth 2.0, JWT)
- **Documentation:** Auto-generate API documentation using FastAPI's OpenAPI support
- **Versioning:** Plan for API versioning from the start (e.g., using URL prefixes `/api/v1/` or headers). Follow semantic versioning for package/library versions. See [semantic-versioning.md](semantic-versioning.md) for comprehensive guidance
- **CORS:** Configure Cross-Origin Resource Sharing (CORS) settings correctly

## Code Example Requirements

When writing implementation code (not during planning):

- All functions must include type annotations
- Must provide clear, Google-style docstrings
- Key logic should be annotated with comments
- Provide usage examples (e.g., in the `tests/` directory or as a `__main__` section)
- Include error handling
- Use `ruff` for code formatting

## Best Practices

- **Prioritize new features in Python 3.10+**
- **When explaining code, provide clear logical explanations and code comments**
- **When making suggestions, explain the rationale and potential trade-offs**
- **If code examples span multiple files, clearly indicate the file name**
- **Do not over-engineer solutions:** Strive for simplicity and maintainability while still being efficient
- **Favor modularity, but avoid over-modularization**
- **Use the most modern and efficient libraries when appropriate**, but justify their use and ensure they are used widely
- **When providing solutions or examples, ensure they are self-contained and executable** without requiring extensive modifications
- **If a request is unclear or lacks sufficient information, ask clarifying questions** before proceeding
- **Always consider the security implications of your code**, especially when dealing with user inputs and external data
- **Actively use and promote best practices** for the specific tasks at hand (LLM app development, data cleaning, demo creation, etc.)

## Core Guidelines

- Always think about and plan your approach to solving the user's task
- Use test-driven-development: Write tests, then write code for them, then execute tests. Iterate on code as needed
- If you are unsure or need to make an assumption, check with the user first
