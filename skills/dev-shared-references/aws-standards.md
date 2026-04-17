# AWS Infrastructure Best Practices & Guidelines

We always do our best to follow AWS best practices for security, scalability, and architecture.

## Default AWS Region

Brain Bridge infrastructure uses **`us-east-1`** as the primary AWS region for all deployments. When configuring CDK stacks, deploy scripts, or any AWS resources, default to `us-east-1` unless there is a specific reason to use another region (e.g., data residency requirements for a customer).

```bash
export CDK_DEFAULT_REGION=us-east-1
export AWS_REGION=us-east-1
```

## 1. Infrastructure as Code (IaC) Architecture

### Multi-Stack Pattern with Dependency Management

- **Separation of Concerns:** Implement separate stacks for different infrastructure layers
  - Example: BrainyDataStack (Secrets Manager, CloudWatch), BrainyAgentsStack (Lambda, DynamoDB), BrainySlackStack (API Gateway, Slack proxy)
- **Stack Independence:** Design stacks to be independently deployable and testable
  - Avoid cross-stack references that create tight coupling
  - Use parameter passing instead of stack interdependencies
- **Parameter Passing:** Pass values between stacks via CloudFormation parameters or SSM Parameter Store
  - Example: Store ARNs in SSM, retrieve in dependent stacks
  - Enables independent deployment and rollback
- **Explicit Dependencies:** Use `add_dependency()` only when deployment ordering is required
- **Staged Deployment:** Orchestrate multi-stack deployments with proper staging

**Parameter Passing Example:**

```python
# Stack A: Export value to SSM Parameter Store
from aws_cdk import aws_ssm as ssm

ssm.StringParameter(self, "TableArnParam",
    parameter_name=f"/{environment}/dynamodb/users-table-arn",
    string_value=users_table.table_arn
)

# Stack B: Import value from SSM Parameter Store
table_arn = ssm.StringParameter.value_from_lookup(
    self, f"/{environment}/dynamodb/users-table-arn"
)

# Benefit: Stacks can be deployed independently
# No tight coupling via stack.export_value() / Fn.import_value()
```

### Environment-Aware Configuration

```json
{
  "environment": "dev",
  "resourcePrefix": "dev-",
  "tags": {
    "customer": "BrainBridge",
    "environment": "dev",
    "application": "brainy"
  }
}
```

### Resource Tagging Standards

**Required Tags (All Resources):**

```python
from aws_cdk import Tags

# Apply to entire stack
Tags.of(self).add("customer", "BrainBridge")
Tags.of(self).add("environment", environment)  # dev, staging, prod
Tags.of(self).add("application", "brainy")
Tags.of(self).add("managed-by", "cdk")
Tags.of(self).add("cost-center", "engineering")

# Per-resource tags for specific tracking
Tags.of(lambda_function).add("function-type", "webhook-handler")
Tags.of(dynamodb_table).add("data-classification", "customer-data")
```

**Tag Guidelines:**

- **customer**: Client/customer name (e.g., "BrainBridge")
- **environment**: Deployment environment (dev, staging, prod)
- **application**: Application/project name (e.g., "brainy", "lindy-integrations")
- **managed-by**: Infrastructure management tool (cdk, terraform, manual)
- **cost-center**: Business unit for cost allocation (engineering, operations)
- **data-classification**: Sensitivity level (public, internal, customer-data, pii)
- **function-type**: Lambda function purpose (webhook-handler, api-endpoint, batch-processor)

**Benefits:**
- Cost allocation and tracking per customer/environment
- Security and compliance auditing
- Resource organization and filtering
- Automated lifecycle management

## 2. Security Best Practices

### Comprehensive Secrets Management

- **AWS Secrets Manager:** Store all sensitive data securely
- **Automatic Generation:** Use `SecretStringGenerator` for secure keys
- **Structured Paths:** Organize naming (e.g., `app/{environment}/lindy-webhook-secrets`)
- **Retention Policies:** `RemovalPolicy.RETAIN` prevents accidental deletion
- **Minimal Permissions:** Grant Lambda functions only necessary access

### IAM Security Model

- **Principle of Least Privilege:** Granular permissions per resource
- **Scoped Access:** Limit DynamoDB and Secrets Manager permissions to specific resources
- **Environment Isolation:** Separate IAM roles per environment

## 3. Serverless Architecture Patterns

### Lambda Architecture and Performance Optimizations

- **Base Image:** Start with AWS image: `FROM public.ecr.aws/lambda/python:3.10`
- **ARM64 Architecture:** Better price-performance ratio, works well locally on Mac + AWS
- **Right-sized Memory:** Test to determine memory needed for your lambda
- **Docker Deployment:** Ensures consistent builds and dependencies
- **Default Handler:** Don't change the default `lambda_handler.handler` in the Dockerfile

## 4. Monitoring & Observability

### Log Retention Strategy

```python
log_retention = RetentionDays.ONE_WEEK  # Cost-effective operational logs
```

### Operational Dashboards

- **Real-time Monitoring:** Custom CloudWatch dashboards
- **Error Rate Calculations:** Automated threshold alerting
- **Cost Tracking:** LLM usage and AWS resource costs

## 5. API Gateway Best Practices

### Logical Route Organization

```
/health                                               # Health checks
/slack/events                                         # Slack webhook (proxy)
/slack/commands/*                                     # Slack commands (main)
/callbacks/lindy/*                                    # Workflow callbacks
/apps/brainy/users/{userId}/sessions/{sessionId}     # ADK
```

### CORS & Security Configuration

- **Proper CORS:** Preflight handling for web clients
- **Environment Stages:** Separate API stages per environment
- **Health Endpoints:** Multiple monitoring points

## 6. Docker & Containerization

### Production-Ready Dockerfile

```dockerfile
# Multi-stage build pattern
FROM public.ecr.aws/lambda/python:3.10-arm64

# Dependency optimization
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Security best practices
USER 1000:1000
```

### Development Environment

```yaml
# docker-compose.yml pattern
services:
  app_name:
    build: .
    environment:
      - AWS_ACCESS_KEY_ID
      - AWS_SECRET_ACCESS_KEY
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```

## 7. Deployment & CI/CD Patterns

### Robust Deployment Script

```bash
# Multi-environment deployment pattern
./deploy.sh dev    # Development deployment
./deploy.sh prod   # Production deployment

# Features:
# - Environment validation
# - CDK bootstrapping
# - API URL extraction
# - Health check verification
# - Deployment timing
```

### Safety Mechanisms

- **Clean Builds:** Remove stale CDK artifacts
- **Environment Isolation:** Prevents cross-environment contamination
- **Approval Control:** Automated deployments with safety checks

## 8. Cost Optimization Strategies

### Resource Right-Sizing

- **Function Memory:** Optimized per use case
- **Architecture Choice:** ARM64 for better price-performance and local testing
- **DynamoDB Billing:** Pay-per-request for variable workloads
- **Log Retention:** Short-term retention for operational logs

### Environment Efficiency

- **Resource Prefixing:** Independent scaling per environment
- **Shared Resources:** Appropriate sharing where security permits

## 9. Error Handling & Resilience

### Comprehensive Error Management

```python
# Secrets Management Error Handling
try:
    secret = await get_secret(secret_arn)
except SecretNotFoundError:
    logger.error(f"Secret {secret_arn} not found")
    return fallback_behavior()
except SecretAccessDeniedError:
    logger.error("Insufficient permissions for secret access")
    raise
```

### Resilience Patterns

- **Retry Logic:** Built into AWS SDK operations
- **Idempotency:** Event deduplication for webhooks
- **Data Protection:** Retention policies for critical resources
- **Graceful Degradation:** Fallback behaviors for service failures

## 10. Step Functions & Orchestration

### Direct Lambda Invocations (No Wrapper Pattern)

Prefer direct Lambda invocations in Step Functions over wrapper Lambdas:

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": {
    "FunctionName": "${LAMBDA_ARN}",
    "Payload": {
      "entity_type": "Task",
      "data.$": "$.inputData"
    }
  },
  "ResultSelector": {
    "records.$": "$.Payload.body.records"
  }
}
```

**Benefits:**
- Fewer Lambda functions to maintain
- Lower latency (no intermediate invocations)
- Simpler debugging (Step Functions history shows all calls)

### States.Format with Special Characters

When using `States.Format` with strings containing curly braces (e.g., Airtable formulas), escape by doubling:

```json
// ❌ WRONG - causes "matching '}' not found" error
"filter.$": "States.Format('AND({Status}=\"Active\")', $.id)"

// ✓ CORRECT - double curly braces for literals
"filter.$": "States.Format('AND({{Status}}=\"Active\")', $.id)"
```

The double braces `{{Status}}` produce literal `{Status}` in the output.

### JSONPath for Fields with Spaces

Use bracket notation for field names containing spaces:

```json
// ❌ WRONG - invalid JSONPath
"task_type.$": "$.task.Task Type"

// ✓ CORRECT - bracket notation
"task_type.$": "$.task['Task Type']"
```

### Map State for Parallel Processing

Use Map state with `MaxConcurrency` for controlled parallelism:

```json
{
  "Type": "Map",
  "ItemsPath": "$.records",
  "MaxConcurrency": 3,
  "ItemProcessor": {
    "ProcessorConfig": { "Mode": "INLINE" },
    "StartAt": "ProcessItem",
    "States": { /* ... */ }
  }
}
```

### Error Handling Patterns

```json
{
  "Retry": [
    {
      "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
      "IntervalSeconds": 2,
      "MaxAttempts": 3,
      "BackoffRate": 2
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.error",
      "Next": "HandleError"
    }
  ]
}
```

### ARN Placeholder Pattern

Use placeholders in definition files, replace during CDK synthesis:

```json
{
  "FunctionName": "${MCP_LAMBDA_ARN}"
}
```

```python
# In CDK stack
definition_str = definition_str.replace(
    "${MCP_LAMBDA_ARN}",
    self.mcp_lambda_arn,
)
```

---

## 11. Multi-Environment Management

### Configuration Strategy

```python
# Environment detection pattern
def get_environment_config(environment: str) -> Dict:
    config_path = f"cdk/config/{environment}.json"
    with open(config_path) as f:
        return json.load(f)

# Resource naming convention
resource_name = f"{config['resourcePrefix']}{base_name}"
```

### Deployment Isolation

- **Separate AWS Accounts/Regions:** Complete environment isolation
- **Resource Tagging:** Consistent tagging for cost allocation
- **Access Controls:** Environment-specific IAM boundaries

---

## 12. IAM Role Limitations & Workarounds

### PowerUser Role Cannot Create Lambdas Directly

The AWS `PowerUserAccess` managed policy does **not** include `iam:PassRole` permission, which is required to create Lambda functions (Lambdas need an execution role).

**Error you'll see:**
```
AccessDeniedException: User is not authorized to perform: iam:PassRole on resource:
arn:aws:iam::ACCOUNT:role/ROLE_NAME because no identity-based policy allows the iam:PassRole action
```

**Workaround: Always Use CDK**

CDK uses bootstrapped roles (`cdk-hnb659fds-cfn-exec-role-*`) that have the necessary permissions. Even for simple single-Lambda deployments, use CDK instead of direct AWS CLI commands.

```python
# Minimal CDK stack for a single Lambda
class SimpleLambdaStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # CDK creates the role automatically with proper permissions
        _lambda.Function(
            self, "Function",
            function_name="my-function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("./lambda_code"),
        )
```

**Why This Works:**
- CDK bootstrap creates CloudFormation execution roles with elevated permissions
- CloudFormation (not you) performs the `iam:PassRole` action
- Your PowerUser role only needs `cloudformation:*` permissions

### When You Need Direct Lambda Creation

If you must create Lambdas directly (not recommended), request these IAM permissions:
```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::*:role/lambda-execution-role-*",
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": "lambda.amazonaws.com"
    }
  }
}
```

---

## 13. Airtable Integration Gotchas

### Filter Formulas with Linked Records Are Unreliable

Complex Airtable formulas using `ARRAYJOIN` and `FIND` on linked record fields often fail silently or return unexpected results.

**Unreliable Pattern:**
```python
# ❌ This filter may not work correctly with linked records
payload = {
    "entity_type": "Task",
    "filter_formula": "AND(FIND('recABC123', ARRAYJOIN({Assignee})), {Status}='Not Started')",
    "max_records": 50,
}
```

**Reliable Pattern - Filter in Python:**
```python
# ✓ Fetch broader dataset, filter in code
def get_tasks_for_assignee(assignee_id: str) -> list[dict]:
    # Fetch all tasks with status filter (simple, reliable)
    payload = {
        "entity_type": "Task",
        "filter_formula": "{Status}='Not Started'",
        "max_records": 100,
    }
    result = invoke_mcp_lambda(MCP_LIST_FUNCTION, payload)
    all_tasks = result.get("records", [])

    # Filter in Python (reliable, debuggable)
    return [
        task for task in all_tasks
        if assignee_id in task.get("assignee", [])
    ]
```

**Why This Is Better:**
- Airtable's formula engine has edge cases with linked records
- Python filtering is predictable and easy to debug
- You can add logging to understand what's being filtered
- Slightly more data transfer, but much more reliable

### Simple Airtable Formulas That Work

These formula patterns are reliable:
```python
# Single field equality
"{Status}='Not Started'"

# Date comparisons
"IS_AFTER({Due Date}, TODAY())"

# Empty/non-empty checks
"{Email}!=''"

# Simple text contains
"FIND('keyword', {Notes})"
```

### Formulas to Avoid

```python
# ❌ Complex linked record lookups
"FIND('recID', ARRAYJOIN({Linked Field}))"

# ❌ Multiple ARRAYJOIN operations
"AND(ARRAYJOIN({Field1}), ARRAYJOIN({Field2}))"

# ❌ Nested functions with linked records
"IF(LEN(ARRAYJOIN({Contacts})) > 0, 'Yes', 'No')"
```
