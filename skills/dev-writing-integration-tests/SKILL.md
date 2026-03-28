---
name: writing-integration-tests
description: Creates comprehensive integration tests when testing interactions between components, databases, APIs, or external services. Uses Testcontainers and proper isolation patterns to verify end-to-end workflows with real dependencies. Also covers testing deployed AWS infrastructure (Lambda, Step Functions, API Gateway) against live environments — use this skill when someone wants to validate a deployment, write live AWS tests, or set up post-deployment smoke tests. Use this skill whenever someone wants to test against real infrastructure instead of mocks — real databases via Testcontainers or Docker, deployed Lambda functions, live Step Functions or API Gateway endpoints. Also triggers for replacing MagicMock with real databases, fixing test isolation or shared database state issues, setting up Docker-based test infrastructure, writing post-deployment verification tests, mixing real services with selective mocks for third-party APIs, or any situation where mocks hide real bugs. Do NOT use for unit tests, mocked tests, or pure logic testing — use dev-writing-unit-tests instead.
---

# Integration Testing Skill

Write tests that verify components work together with real dependencies — not mocks. This skill covers two complementary testing modes:

1. **Local integration tests** — Testcontainers/Docker Compose with real databases and services
2. **Live AWS tests** — Validate deployed Lambda, Step Functions, and API Gateway against real environments

Use the TodoWrite tool to track progress through these phases.

---

## Phase 1: Choose Your Testing Mode

First, determine which type of integration test you need.

### Local Integration Tests (Testcontainers/Docker)

Use when testing:
- Database operations (queries, constraints, transactions)
- API endpoints with real database backends
- Multi-component workflows (registration → email → login)
- External service integration (payment gateways, message queues)
- Any interaction between 2+ components

### Live AWS Tests

Use when testing:
- Deployed Lambda functions work with real credentials and secrets
- Step Function orchestration routes correctly between Lambdas
- API Gateway endpoints respond correctly after deployment
- IAM permissions are configured correctly
- Lambda environment variables and layers work in production

**Rule of thumb:** Test business logic locally with containers. Test infrastructure configuration against live AWS.

See `references/live-aws-testing.md` for complete live AWS patterns including `aws_config.py` helpers, `conftest.py` fixtures, Lambda/Step Function test patterns, and the `@pytest.mark.live_aws` marker.

### Don't Use Integration Tests For

- Pure logic or individual functions (use unit tests — faster feedback)
- Every edge case (cover in unit tests, happy path in integration)
- Isolated validation rules (unit tests are sufficient)

**Testing pyramid target:** 70% unit, 20% integration, 10% E2E.

---

## Phase 2: Set Up Test Infrastructure

### Local: Testcontainers Setup

Testcontainers spins up real services in Docker — automatic cleanup, dynamic ports, 1-3 second startup.

```python
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="module")
def database_engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def database_session(database_engine):
    """Each test gets a transaction that rolls back — clean state guaranteed."""
    connection = database_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

This pattern is the foundation: container starts once (fast), each test gets isolated data (transaction rollback), cleanup is automatic. See `references/external-services-testing.md` for Redis, MongoDB, Kafka, Elasticsearch patterns and Docker Compose setup.

### Live AWS: Environment Setup

```bash
# Verify credentials before testing
aws sts get-caller-identity --profile ${AWS_PROFILE}
```

Add markers to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "live_aws: marks tests that run against live AWS resources",
]
```

Create `tests/live_aws/aws_config.py` for resource names, ARN construction, and helpers (invoke_lambda_sync, start_execution, wait_for_execution). Create `tests/live_aws/conftest.py` with session-scoped AWS client fixtures. Full examples in `references/live-aws-testing.md`.

### Windows Note

On Windows, avoid shell redirection (`>`, `>>`) for creating test files — it can corrupt files with null bytes, breaking pytest. Use the Write tool or `Path.write_text("", encoding="utf-8")` instead.

---

## Phase 3: Write Integration Tests

Every integration test should use `@pytest.mark.integration` (or `@pytest.mark.live_aws` for AWS tests).

### Local: Database Integration

```python
@pytest.mark.integration
def test_create_user_persists_to_database(database_session):
    user = User(username="john", email="john@example.com")
    database_session.add(user)
    database_session.commit()

    retrieved = database_session.query(User).filter_by(username="john").first()
    assert retrieved is not None
    assert retrieved.email == "john@example.com"
```

### Local: API + Database Integration

```python
@pytest.mark.integration
def test_create_order_endpoint(api_client, database_session):
    response = api_client.post('/orders', json={"product_id": 123, "quantity": 2})
    assert response.status_code == 201

    order = database_session.query(Order).first()
    assert order is not None
    assert order.quantity == 2
```

### Local: Multi-Step Workflow

```python
@pytest.mark.integration
def test_user_registration_flow(api_client, database_session, mock_email):
    # Register
    response = api_client.post('/auth/register', json={...})
    assert response.status_code == 201

    # Verify unverified in DB
    user = database_session.query(User).first()
    assert user.is_verified is False

    # Verify email sent
    mock_email.send.assert_called_once()

    # Complete verification and login
    api_client.post('/auth/verify', json={...})
    login = api_client.post('/auth/login', json={...})
    assert login.status_code == 200
```

### Live AWS: Lambda Test

```python
pytestmark = [pytest.mark.live_aws, pytest.mark.integration]

class TestMyLambda:
    def test_success_case(self, lambda_client, verify_lambda_exists):
        result = invoke_lambda_sync(
            lambda_client, MY_LAMBDA_FUNCTION, {"key": "value"}
        )
        assert result["status_code"] == 200
        assert result["function_error"] is None
        assert result["payload"]["statusCode"] == 200

    def test_validation_error(self, lambda_client, verify_lambda_exists):
        result = invoke_lambda_sync(lambda_client, MY_LAMBDA_FUNCTION, {})
        assert result["payload"]["statusCode"] == 400
```

### Live AWS: Step Function Test

```python
pytestmark = [pytest.mark.live_aws, pytest.mark.integration]

class TestMyWorkflow:
    def test_successful_execution(self, sfn_client, verify_state_machine_exists):
        execution_arn = start_execution(
            sfn_client, MY_STATE_MACHINE_ARN,
            {"messages": [{"type": "TEST", "data": "sample"}]}
        )
        result = wait_for_execution(sfn_client, execution_arn)
        assert result["status"] == "SUCCEEDED"
```

For more patterns (error scenarios, batch processing, timeout handling), see `references/live-aws-testing.md`. For complete local test file templates including conftest.py, see `templates/integration-test-template.md`.

---

## Phase 4: Ensure Test Isolation

Each test must be independent — passing regardless of execution order.

**Local tests:** Use the transaction rollback pattern from Phase 2. Container starts once (module scope), each test gets a session (function scope), transaction rolls back after each test. No cleanup code needed.

**Live AWS tests:** Use unique execution names (uuid-based) so concurrent test runs don't collide. Session-scoped AWS client fixtures avoid redundant authentication.

**Verify independence:**
```bash
uv run pytest -m integration --random-order    # Random order
uv run pytest -k test_specific_integration     # Single test
uv run pytest -m integration -n auto           # Parallel
```

---

## Phase 5: Organize and Tag

### Test File Structure

```
tests/
├── unit/                         # Fast unit tests (<100ms each)
│   └── test_*.py
├── integration/                  # Local integration tests (<5s each)
│   ├── conftest.py
│   ├── test_user_api.py
│   └── test_order_workflow.py
├── live_aws/                     # Live AWS tests
│   ├── __init__.py
│   ├── aws_config.py
│   ├── conftest.py
│   ├── test_live_lambda.py
│   └── test_live_step_function.py
└── conftest.py                   # Shared fixtures
```

### Marker Strategy

```python
@pytest.mark.integration                    # Local integration test
@pytest.mark.integration @pytest.mark.slow  # Expensive local test
@pytest.mark.live_aws                       # Requires real AWS credentials
@pytest.mark.timeout(30)                    # Timeout protection for containers
```

### Running Selectively

```bash
uv run pytest -m integration                     # All local integration
uv run pytest -m "not integration and not live_aws"  # Unit tests only (fast)
uv run pytest -m live_aws -v                     # Live AWS tests
uv run pytest -m "integration and not slow"      # Fast integration only
```

---

## Phase 6: Optimize Performance

Target: **<5 seconds** per local integration test. Live AWS tests may take longer (30-120s for Step Functions).

**Key strategies:**
1. **Reuse containers** — module/session scope, not function scope
2. **Transaction rollback** — faster than DELETE statements
3. **Minimal test data** — only create what the test needs
4. **Parallel execution** — `pytest -m integration -n auto`
5. **Alpine images** — `postgres:15-alpine` is smaller and faster

---

## Phase 7: Validate and Finalize

### Integration Test Checklist

- [ ] Tests actual integration between 2+ components (not just logic)
- [ ] Uses real dependencies (containers or live AWS)
- [ ] Tagged with `@pytest.mark.integration` or `@pytest.mark.live_aws`
- [ ] Test data isolated (transaction rollback or unique execution names)
- [ ] Tests realistic workflow or scenario
- [ ] Local tests complete in <5 seconds
- [ ] Independent of other tests (verified with `--random-order`)
- [ ] Descriptive name explaining the integration being tested

Run [dev-quality-checks](../dev-quality-checks/SKILL.md) for comprehensive validation.

---

## Supporting Files Reference

### Integration Testing Specific
- `references/integration-test-design.md` — What to test, patterns, testing pyramid, common mistakes
- `references/external-services-testing.md` — Testcontainers (Postgres, Redis, MongoDB, Kafka, Elasticsearch), Docker Compose, FastAPI test client, API mocking
- `references/live-aws-testing.md` — Testing deployed AWS infrastructure with pytest: aws_config.py helpers, conftest.py fixtures, Lambda/Step Function patterns, CI/CD integration, troubleshooting
- `templates/integration-test-template.md` — Complete test file templates with conftest.py

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` — Python best practices, type hints, docstrings
- `../dev-shared-references/git-conventions.md` — Commit message format and workflow
- `../dev-shared-references/uv-guide.md` — Dependency management with uv

---

## Key Principles

- **Real dependencies, not mocks** — The whole point of integration tests is testing real interactions
- **Two modes** — Local containers for component integration, live AWS for infrastructure validation
- **Transaction rollback** — Fast, reliable isolation without cleanup code
- **Realistic scenarios** — Test complete workflows, not just CRUD operations
- **Selective execution** — Tag properly so unit tests stay fast, integration runs before merge
- **Performance** — Container reuse + transactions + Alpine images = fast tests
