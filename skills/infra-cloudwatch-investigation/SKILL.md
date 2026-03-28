---
name: infra-cloudwatch-investigation
description: Investigate Lambda, Step Function, and agent failures using CloudWatch logs. Use when debugging deployed AWS infrastructure that isn't behaving correctly. Triggers for production errors, post-deployment validation, credential/secrets issues, Lambda timeouts, Step Function failures, agent pipeline debugging, or when something "works locally but not in AWS." Also use when the user says "check the logs", "why is this Lambda failing", "the deployment didn't work", "records aren't being created", "agent is returning wrong results", or any situation where CloudWatch logs would help diagnose the problem — even if they don't explicitly mention CloudWatch.
---
# CloudWatch Log Investigation

Systematically pull and analyze CloudWatch logs from Lambda functions, Step Functions, and agent pipelines to diagnose production failures.

Use the TodoWrite tool to track progress through these phases.

---

## Phase 1: Identify Target Resources

Before pulling logs, figure out which resources are involved. The user may give you a Lambda name, a general area ("the campaign creator is broken"), or just a symptom ("records aren't showing up in Airtable").

### Discover Log Groups

```bash
# Find Lambda log groups by prefix
AWS_PROFILE=${PROFILE} aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/${PREFIX}" \
  --region ${REGION} --query 'logGroups[].logGroupName'

# Find Step Function log groups
AWS_PROFILE=${PROFILE} aws logs describe-log-groups \
  --log-group-name-prefix "/aws/vendedlogs/states/" \
  --region ${REGION} --query 'logGroups[].logGroupName'

# List Lambda functions matching a pattern
AWS_PROFILE=${PROFILE} aws lambda list-functions \
  --region ${REGION} \
  --query "Functions[?contains(FunctionName, '${PATTERN}')].FunctionName"
```

### Check Step Function Executions

```bash
AWS_PROFILE=${PROFILE} aws stepfunctions list-executions \
  --state-machine-arn "${SFN_ARN}" --max-results 5 --region ${REGION}
```

See `references/aws-log-patterns.md` for Lambda naming conventions and log group patterns specific to Brain Bridge infrastructure (bb-gtm, bb-os-mcp, AIT agents, Brainy).

---

## Phase 2: Pull Recent Logs

Always check **at least 2-3 recent log streams** — a single stream might not show the failure. For time-sensitive issues, use CloudWatch Insights to search across all streams at once.

### Get Latest Log Streams

```bash
AWS_PROFILE=${PROFILE} aws logs describe-log-streams \
  --log-group-name "${LOG_GROUP}" \
  --order-by LastEventTime --descending --max-items 3 \
  --region ${REGION}
```

### Pull Log Events

```bash
# Save logs to file first, then parse
AWS_PROFILE=${PROFILE} aws logs get-log-events \
  --log-group-name "${LOG_GROUP}" \
  --log-stream-name "${STREAM_NAME}" \
  --region ${REGION} --limit 200 \
  --output json > /tmp/logs_output.json

# Parse and filter noise
python3 -c "
import json
with open('/tmp/logs_output.json') as f:
    data = json.load(f)
noise = ['event loop', 'logging_worker', 'mixins.py', 'queues.py',
         '^^^^^^', 'RuntimeError: <Queue', 'getter =', 'task = await']
for e in data.get('events', []):
    msg = e['message'].strip()
    if msg and not any(n in msg for n in noise):
        print(msg)
"
```

### Time-Based Log Queries

```bash
# Logs from the last N minutes (useful for recent failures)
AWS_PROFILE=${PROFILE} aws logs tail \
  "${LOG_GROUP}" --since 30m --region ${REGION}

# Logs in a specific time window
AWS_PROFILE=${PROFILE} aws logs filter-log-events \
  --log-group-name "${LOG_GROUP}" \
  --start-time ${EPOCH_MS_START} --end-time ${EPOCH_MS_END} \
  --region ${REGION}
```

### CloudWatch Insights (for complex searches)

CloudWatch Insights is far more powerful than basic log queries — use it when you need to search across all streams, aggregate errors, or find patterns. The query language supports filtering, parsing, aggregation, and sorting.

```bash
# Start an Insights query — searches ALL streams in the log group
QUERY_ID=$(AWS_PROFILE=${PROFILE} aws logs start-query \
  --log-group-name "${LOG_GROUP}" \
  --start-time $(date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message
    | filter @message like /ERROR|Exception|Traceback/
    | sort @timestamp desc
    | limit 50' \
  --region ${REGION} \
  --query 'queryId' --output text)

# Wait a few seconds, then get results
sleep 3
AWS_PROFILE=${PROFILE} aws logs get-query-results \
  --query-id "${QUERY_ID}" --region ${REGION}
```

**Common Insights queries:**

```
# Count errors by type over the last hour
fields @timestamp, @message
| filter @message like /ERROR/
| parse @message "* - ERROR - *" as component, error_msg
| stats count(*) as error_count by error_msg
| sort error_count desc

# Find cold starts and their duration
filter @type = "REPORT"
| filter ispresent(@initDuration)
| stats avg(@initDuration) as avg_cold_start, max(@initDuration) as max_cold_start, count(*) as cold_start_count

# Find Lambda timeouts
filter @message like /Task timed out/
| fields @timestamp, @requestId, @message
| sort @timestamp desc

# Track LLM costs per invocation
filter @message like /Completion cost/
| parse @message "cost=$* USD" as cost
| stats sum(cost) as total_cost, count(*) as llm_calls
```

---

## Phase 3: Filter Known Noise

CloudWatch logs from Lambda-based agents contain significant noise. Filtering it out early saves time and prevents misdiagnosis.

### litellm LoggingWorker Errors (Safe to Ignore)

These appear on warm Lambda invocations and are harmless:
```
RuntimeError: <Queue at 0x... maxsize=50000> is bound to a different event loop
File "litellm/litellm_core_utils/logging_worker.py"
```

Caused by litellm's asyncio.Queue created during cold start not working on the new event loop. Background logging only — the actual LLM call still succeeds.

### ADK Deprecation Warnings (Safe to Ignore)

```
[WARNING] Deprecated. Please migrate to the async method.
```

### What IS Meaningful

- `[ERROR]` lines NOT containing "LoggingWorker" or "event loop"
- `INIT Duration` and `Duration` in REPORT lines
- `lambda_handler - INFO` lines showing actual business logic
- `Completion cost:` lines showing LLM calls and token counts
- `Gateway invocation completed, response length:` showing what was returned
- Any `Traceback` NOT related to litellm
- `Task timed out after` — Lambda hit its timeout limit

---

## Phase 4: Analyze Execution Flow

### Lambda Execution Metrics

From REPORT lines, extract:
- **Duration**: How long the Lambda ran
- **Memory Used**: Peak memory consumption
- **Init Duration**: Cold start time (if present — only on first invocation of a container)
- **Billed Duration**: What you're paying for

A pattern of increasing Duration across invocations can indicate a memory leak or accumulating state.

### Agent LLM Call Analysis

From `Completion cost:` lines:
- Count total LLM calls per invocation
- Sum token usage and cost
- Identify if agent is looping (many calls with low tokens = the agent keeps retrying or going in circles)

### Error Rate Aggregation

When investigating intermittent issues, aggregate error patterns rather than looking at individual log entries:

```bash
# Use Insights to count errors over time
QUERY_ID=$(AWS_PROFILE=${PROFILE} aws logs start-query \
  --log-group-name "${LOG_GROUP}" \
  --start-time $(date -v-24H +%s) \
  --end-time $(date +%s) \
  --query-string 'filter @message like /ERROR/
    | stats count(*) as errors by bin(1h) as hour
    | sort hour desc' \
  --region ${REGION} \
  --query 'queryId' --output text)

sleep 3
AWS_PROFILE=${PROFILE} aws logs get-query-results \
  --query-id "${QUERY_ID}" --region ${REGION}
```

### Step Function Analysis

```bash
# Get execution history — focus on failures
AWS_PROFILE=${PROFILE} aws stepfunctions get-execution-history \
  --execution-arn "${EXECUTION_ARN}" --region ${REGION} \
  --query 'events[?type==`TaskFailed` || type==`ExecutionFailed` || type==`TaskSucceeded`]'

# Get the error details from a failed execution
AWS_PROFILE=${PROFILE} aws stepfunctions describe-execution \
  --execution-arn "${EXECUTION_ARN}" --region ${REGION} \
  --query '{status: status, error: error, cause: cause}'
```

---

## Phase 5: Cross-Lambda Correlation

### Trace an Agent Pipeline

For multi-Lambda agent flows (e.g., Brainy -> Gateway -> Sub-Agent -> MCP tools):

1. **Main Agent Lambda**: Find the initial request and tool call
2. **Gateway Lambda**: Find the routing decision
3. **Sub-Agent Lambda**: Find the execution and any errors
4. **MCP Tool Lambdas**: Find the actual data operations (creates, reads, updates)

### Correlate by Timestamp

Agent pipeline executions happen in sequence. Match timestamps across Lambda log groups:
- Main agent call starts at T0
- Gateway routes at T0 + 1-2s
- Sub-agent starts at T0 + 2-5s
- MCP tool calls at T0 + Ns

Use CloudWatch Insights to search multiple log groups simultaneously:

```bash
# Search across multiple Lambda log groups
QUERY_ID=$(AWS_PROFILE=${PROFILE} aws logs start-query \
  --log-group-names "/aws/lambda/agent-main" "/aws/lambda/gateway" "/aws/lambda/sub-agent" \
  --start-time $(date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @logStream, @message
    | filter @message like /ERROR|error|Exception/
    | sort @timestamp asc
    | limit 100' \
  --region ${REGION} \
  --query 'queryId' --output text)
```

---

## Phase 6: Produce Investigation Report

After completing the investigation, produce a structured report. Use the template in `templates/investigation-report.md`.

The report should include:
- **What was investigated** — which resources, what time window
- **What was found** — errors, patterns, root cause
- **Evidence** — relevant log entries, metrics, timestamps
- **Recommendation** — what to fix and how

---

## Key Principles

- **Check multiple log streams** — a single stream might miss the failure
- **Filter noise first** — litellm LoggingWorker errors dominate CloudWatch
- **Use Insights for complex searches** — it's dramatically more powerful than get-log-events
- **Aggregate error patterns** — individual errors mislead; trends tell the real story
- **Cross-correlate timestamps** across Lambda log groups for pipeline tracing
- **Check REPORT lines** for duration, memory, cold start metrics
- **Check for zero executions** — Step Functions with 0 executions were never triggered

## Common Mistakes to Avoid

- Don't assume litellm RuntimeErrors are real failures (they're background logging noise)
- Don't look only at the most recent log stream — check 2-3 recent streams
- Don't forget that agent Lambdas are stateless — each invocation is fresh
- Don't use only `get-log-events` when Insights would be faster and more comprehensive
- Don't report raw log output without filtering noise and identifying the actual error

## Reference

See `references/aws-log-patterns.md` for Lambda naming conventions, log group patterns, known noise patterns, and troubleshooting recipes (including credential caching, Secrets Manager access, and post-deployment validation).
