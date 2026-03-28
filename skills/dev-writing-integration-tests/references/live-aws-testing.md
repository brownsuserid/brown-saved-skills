# Live AWS Infrastructure Testing

Testing deployed AWS infrastructure (Lambda, Step Functions, API Gateway) against real environments. This complements local integration testing (Testcontainers) by validating that deployed resources work correctly with real credentials, IAM permissions, and service integrations.

## Table of Contents

1. [When to Use Live vs Local Tests](#when-to-use-live-vs-local-tests)
2. [Test Architecture](#test-architecture)
3. [Environment Setup](#environment-setup)
4. [Writing Live AWS Tests](#writing-live-aws-tests)
5. [Running Tests](#running-tests)
6. [Common Issues](#common-issues)
7. [CI/CD Integration](#cicd-integration)

---

## When to Use Live vs Local Tests

Live AWS tests catch issues that only appear in real AWS environments — IAM permission gaps, Secrets Manager access, environment variable configuration, and service-to-service connectivity.

| Scenario | Local Integration Test | Live AWS Test |
|----------|----------------------|---------------|
| Business logic processing | Yes — fast, isolated | No |
| Database queries/constraints | Yes — Testcontainers | No |
| Lambda with Secrets Manager | No | Yes — validates secret access and format |
| Step Function orchestration | No | Yes — validates Lambda ARNs and routing |
| API Gateway routing/auth | No | Yes — validates real endpoint behavior |
| IAM permission correctness | No | Yes — only testable against real AWS |
| Lambda environment variables | No | Yes — validates deployed configuration |
| Lambda layer dependencies | No | Yes — validates real runtime environment |
| Pure AWS SDK calls | Maybe — LocalStack | Yes — if LocalStack doesn't cover it |

**Rule of thumb:** Test business logic locally, test infrastructure configuration live.

---

## Test Architecture

```
tests/
├── unit/                    # Mocked tests, fast, no AWS needed
├── integration/             # LocalStack or Testcontainers
└── live_aws/                # Real AWS resources
    ├── __init__.py
    ├── aws_config.py        # Constants, ARNs, helper functions
    ├── conftest.py          # pytest fixtures for AWS clients
    ├── test_live_lambda.py  # Lambda invocation tests
    └── test_live_step_function.py  # Step Function tests
```

Live AWS tests live alongside unit and integration tests but use a separate `live_aws` pytest marker so they can be excluded in CI environments without AWS credentials.

---

## Environment Setup

### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_PROFILE` | Yes | — | AWS credentials profile |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `AWS_ACCOUNT_ID` | No | — | For constructing ARNs |
| `ENVIRONMENT` | No | `dev` | Target environment (dev/staging/prod) |

For specific integrations (add as needed):

| Variable | Description |
|----------|-------------|
| `TEST_EMAIL_RECIPIENT` | Email address for email-sending Lambda tests |
| `TEST_SENDER_ALIAS` | Credential alias for email tests |

### pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests",
    "live_aws: marks tests that run against live AWS resources",
]
```

### Verify Credentials Before Testing

```bash
aws sts get-caller-identity --profile ${AWS_PROFILE}
```

---

## Writing Live AWS Tests

### aws_config.py — Configuration and Helpers

This module centralizes resource names, ARN construction, and helper functions shared across test files.

```python
"""AWS configuration and helper functions for live tests."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

# Configuration
AWS_PROFILE = os.environ.get("AWS_PROFILE", "default")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "123456789012")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
RESOURCE_PREFIX = f"my-project-{ENVIRONMENT}"  # Change to your project

# Lambda Function Names
MY_LAMBDA_FUNCTION = f"{RESOURCE_PREFIX}-my-lambda"

# Step Function ARNs
MY_STATE_MACHINE_ARN = (
    f"arn:aws:states:{AWS_REGION}:{AWS_ACCOUNT_ID}:"
    f"stateMachine:{RESOURCE_PREFIX}-my-workflow"
)


def invoke_lambda_sync(
    client: Any, function_name: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Invoke a Lambda synchronously and return parsed response."""
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return {
        "status_code": response["StatusCode"],
        "function_error": response.get("FunctionError"),
        "payload": json.loads(response["Payload"].read()),
    }


def start_execution(
    client: Any,
    state_machine_arn: str,
    input_data: dict[str, Any],
    execution_name: str | None = None,
) -> str:
    """Start a Step Function execution and return the execution ARN."""
    if execution_name is None:
        execution_name = f"test-{uuid.uuid4().hex[:8]}-{int(time.time())}"
    response = client.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps(input_data),
    )
    return response["executionArn"]


def wait_for_execution(
    client: Any,
    execution_arn: str,
    timeout_seconds: int = 60,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Poll until Step Function execution completes or timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        response = client.describe_execution(executionArn=execution_arn)
        if response["status"] in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
            return response
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Execution did not complete within {timeout_seconds}s: {execution_arn}"
    )
```

### conftest.py — Fixtures

```python
"""pytest fixtures for live AWS integration tests."""

from __future__ import annotations

from typing import Any

import boto3
import pytest

from .aws_config import (
    AWS_PROFILE,
    AWS_REGION,
    MY_LAMBDA_FUNCTION,
    MY_STATE_MACHINE_ARN,
)


@pytest.fixture(scope="session")
def aws_session() -> boto3.Session:
    """Create AWS session using configured profile."""
    return boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)


@pytest.fixture(scope="session")
def lambda_client(aws_session: boto3.Session) -> Any:
    return aws_session.client("lambda")


@pytest.fixture(scope="session")
def sfn_client(aws_session: boto3.Session) -> Any:
    return aws_session.client("stepfunctions")


@pytest.fixture(scope="session")
def secrets_client(aws_session: boto3.Session) -> Any:
    return aws_session.client("secretsmanager")


@pytest.fixture(scope="session")
def verify_lambda_exists(lambda_client: Any) -> None:
    """Verify Lambda functions exist before running tests — fail fast."""
    for func_name in [MY_LAMBDA_FUNCTION]:
        try:
            lambda_client.get_function(FunctionName=func_name)
        except lambda_client.exceptions.ResourceNotFoundException:
            pytest.fail(f"Lambda not found: {func_name}")


@pytest.fixture(scope="session")
def verify_state_machine_exists(sfn_client: Any) -> None:
    """Verify Step Functions exist before running tests."""
    try:
        sfn_client.describe_state_machine(stateMachineArn=MY_STATE_MACHINE_ARN)
    except sfn_client.exceptions.StateMachineDoesNotExist:
        pytest.fail(f"State Machine not found: {MY_STATE_MACHINE_ARN}")
```

### Test Patterns

#### Lambda Tests

```python
"""Live AWS Lambda tests."""

from __future__ import annotations

from typing import Any

import pytest

from .aws_config import MY_LAMBDA_FUNCTION, invoke_lambda_sync

pytestmark = [pytest.mark.live_aws, pytest.mark.integration]


class TestMyLambda:
    def test_success_case(
        self, lambda_client: Any, verify_lambda_exists: None
    ) -> None:
        result = invoke_lambda_sync(
            lambda_client, MY_LAMBDA_FUNCTION, {"key": "value"}
        )
        assert result["status_code"] == 200
        assert result["function_error"] is None
        assert result["payload"]["statusCode"] == 200

    def test_validation_error(
        self, lambda_client: Any, verify_lambda_exists: None
    ) -> None:
        result = invoke_lambda_sync(lambda_client, MY_LAMBDA_FUNCTION, {})
        assert result["status_code"] == 200  # Invocation succeeded
        assert result["payload"]["statusCode"] == 400  # Business logic rejected
```

#### Step Function Tests

```python
"""Live AWS Step Function tests."""

from __future__ import annotations

import json
from typing import Any

import pytest

from .aws_config import (
    MY_STATE_MACHINE_ARN,
    start_execution,
    wait_for_execution,
)

pytestmark = [pytest.mark.live_aws, pytest.mark.integration]


class TestMyWorkflow:
    def test_successful_execution(
        self, sfn_client: Any, verify_state_machine_exists: None
    ) -> None:
        execution_arn = start_execution(
            sfn_client,
            MY_STATE_MACHINE_ARN,
            {"messages": [{"type": "TEST", "data": "sample"}]},
        )
        result = wait_for_execution(sfn_client, execution_arn)
        assert result["status"] == "SUCCEEDED"

    def test_batch_processing(
        self, sfn_client: Any, verify_state_machine_exists: None
    ) -> None:
        input_data = {
            "messages": [
                {"type": "TYPE_A", "payload": {"id": 1}},
                {"type": "TYPE_B", "payload": {"id": 2}},
            ]
        }
        execution_arn = start_execution(
            sfn_client, MY_STATE_MACHINE_ARN, input_data
        )
        result = wait_for_execution(sfn_client, execution_arn, timeout_seconds=120)
        assert result["status"] == "SUCCEEDED"
        output = json.loads(result["output"])
        assert len(output) == len(input_data["messages"])

    def test_error_handling(
        self, sfn_client: Any, verify_state_machine_exists: None
    ) -> None:
        execution_arn = start_execution(
            sfn_client, MY_STATE_MACHINE_ARN, {"invalid": "data"}
        )
        result = wait_for_execution(sfn_client, execution_arn)
        assert result["status"] in ["SUCCEEDED", "FAILED"]
```

---

## Running Tests

```bash
# All live AWS tests
uv run pytest tests/live_aws -v -m live_aws

# Specific test file
uv run pytest tests/live_aws/test_live_lambda.py -v

# Specific test pattern
uv run pytest tests/live_aws -v -k "success"

# With environment variables for email tests
TEST_EMAIL_RECIPIENT=me@example.com uv run pytest tests/live_aws -v -k "email"

# Exclude live tests (for CI without AWS credentials)
uv run pytest -m "not live_aws"
```

---

## Common Issues

### Lambda returns "Missing credentials in environment variables"

Lambda can't access Secrets Manager or an environment variable isn't set.

1. Check Lambda has the required env var (e.g., `CREDENTIALS_SECRET`)
2. Verify IAM role has `secretsmanager:GetSecretValue` permission
3. Verify the secret exists and has the expected JSON structure

### Lambda caching old credentials (cold start issue)

Warm Lambda containers cache credentials in memory. If you've updated a secret but the Lambda still uses old values:

```bash
# Force cold start by updating an environment variable
aws lambda update-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --environment "Variables={...,CACHE_BUST=$(date +%s)}"

# Wait for the update to complete
aws lambda wait function-updated --function-name ${FUNCTION_NAME}
```

Then re-run your tests.

### "Unable to refresh token" (OAuth Lambdas)

The OAuth refresh token stored in Secrets Manager has expired or been revoked.

1. Re-authenticate via the OAuth flow to get a new refresh token
2. Update the secret in Secrets Manager with the new token
3. Force a cold start on the Lambda (see above) so it picks up the new token

### Step Function "ExecutionFailed"

1. Check execution history: `aws stepfunctions get-execution-history --execution-arn ${ARN}`
2. Verify Lambda ARNs in the state machine definition match deployed functions
3. Check the Step Function IAM role has `lambda:InvokeFunction` permission

### Tests timeout

1. Increase `timeout_seconds` in `wait_for_execution()`
2. Check Lambda timeout settings in the function configuration
3. If Lambda is in a VPC, verify security group and NAT Gateway config

### Tests pass locally but fail in CI

1. CI may use a different AWS profile or region
2. Ensure CI has correct IAM permissions for `lambda:InvokeFunction` and `states:StartExecution`
3. Consider using `pytest -m "not live_aws"` in CI if AWS credentials aren't available

---

## CI/CD Integration

Live AWS tests typically run only in environments with AWS credentials:

```yaml
# GitHub Actions example
jobs:
  test:
    steps:
      - name: Run unit and integration tests
        run: uv run pytest -m "not live_aws" -v

  live-aws-tests:
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - name: Run live AWS tests
        run: uv run pytest -m live_aws -v
```

---

## Related Skills

- When live tests fail and you need to investigate CloudWatch logs: see `../../infra-cloudwatch-investigation/SKILL.md`
- For CDK infrastructure quality validation before deployment: see `../../infra-cdk-quality/SKILL.md`
