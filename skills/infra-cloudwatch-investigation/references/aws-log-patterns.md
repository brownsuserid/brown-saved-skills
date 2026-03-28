# AWS Log Patterns Reference

Common Lambda naming conventions, log group patterns, and troubleshooting recipes for Brain Bridge infrastructure.

## Lambda Naming Conventions

### bb-gtm (GTM Infrastructure)

Pattern: `bb-gtm-{customer}-{env}-{module}-{resource}`

| Module | Example | Purpose |
|--------|---------|---------|
| campaign | `bb-gtm-brain-bridge-dev-campaign-apollo-search` | Campaign Creator pipeline |
| outreach | `bb-gtm-brain-bridge-dev-outreach-filter-deals` | Outreach Manager pipeline |
| stage-mgr | `bb-gtm-brain-bridge-dev-stage-mgr-group-deals` | GTM Stage Manager |
| comm | `bb-gtm-brain-bridge-dev-comm-send-google-mail` | Communication sending |
| commlog | `bb-gtm-dev-commlog-ingest-emails` | Communication logging |
| executor | `bb-gtm-brain-bridge-dev-executor-refresh-context` | Task executor |
| planner | `bb-gtm-brain-bridge-dev-planner-provide-context` | Planning agent |

### bb-os-mcp (MCP Server Lambdas)

Pattern: `bb-os-mcp-{service}-{operation}-{env}`

| Service | Lambdas | Purpose |
|---------|---------|---------|
| at (Airtable) | list, get, create, update, delete, schema | Airtable CRUD via MCP |
| apollo | search-people, enrich-contact, get-person | Apollo.io API via MCP |

### AIT (AI Teammate Agent Lambdas)

CDK auto-generates names: `AITBrainbridgeDevStage-Ag-{AgentName}Agent-{hash}`

| Agent | Example | Purpose |
|-------|---------|---------|
| CampaignCreatorBrain | `AITBrainbridgeDevStage-Ag-CampaignCreatorBrainAgen-77HlOXoQn7pI` | Campaign creation agent |
| OutreachManagerBrain | `AITBrainbridgeDevStage-Ag-OutreachManagerBrainAgen-FOGApiyHUjoc` | Outreach management agent |
| Gratje | `AITBrainbridgeDevStage-Ag-GratjeAgentLambda8B0F073-T0ZpNyxhrv6B` | Main executor agent |
| Oscar | `AITBrainbridgeDevStage-Ag-OscarAgentLambda05436E68-HmekUXJ1HTAN` | Oscar agent |
| GtmStageManager | `AITBrainbridgeDevStage-Ag-GtmStageManagerAgentLamb-XOnSQKb583zo` | Stage manager agent |
| GatewayProvider | `AITBrainbridgeDevStage-Ag-GatewayProviderLambda71C-{hash}` | AgentCore Gateway |

### Brainy (Main Agent)

| Env | Lambda | Purpose |
|-----|--------|---------|
| dev | `dev-bb-ait` | Main Brainy agent (dev) |
| prod | `bb-ait` | Main Brainy agent (prod) |
| slack | `dev-bb-ait-slack-proxy` | Slack event handler |

---

## Log Group Patterns

### Finding Log Groups

```bash
# GTM Lambdas
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/bb-gtm"

# MCP Lambdas
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/bb-os-mcp"

# Agent Lambdas (CDK-named)
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/AITBrainbridge"

# Brainy main agent
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/dev-bb-ait"

# Step Function logs
MSYS_NO_PATHCONV=1 aws logs describe-log-groups \
  --log-group-name-prefix "/aws/vendedlogs/states/"
```

---

## Known Noise Patterns

### litellm LoggingWorker (Safe to Ignore)

```
[ERROR] Task exception was never retrieved
future: <Task finished name='Task-N' coro=<LoggingWorker._worker_loop() done> exception=RuntimeError(...)>
RuntimeError: <Queue at 0x... maxsize=50000 tasks=N> is bound to a different event loop
```

This is a litellm bug on warm Lambda invocations. The asyncio.Queue from cold start doesn't work on the new event loop. Background logging only - not blocking.

### ADK Deprecation Warning (Safe to Ignore)

```
[WARNING] Deprecated. Please migrate to the async method.
```

### Agent Cost Tracking (Informational)

```
brainy.utils.llm - INFO - Completion cost: model=unknown, input_tokens=0, output_tokens=288, total_tokens=288, cost=$0.004320 USD
brainy.utils.llm - INFO - ADK callback triggered for model unknown with 288 tokens
```

These track LLM usage per agent invocation. Useful for cost analysis.

---

## Troubleshooting Recipes

### Recipe 1: Agent Not Creating Records

**Symptom:** Agent says it created records but nothing appears in Airtable.

**Check:**
1. Pull MCP create Lambda logs (`bb-os-mcp-at-create-dev`) - was it invoked?
2. If no logs: Agent may be using internal tools, not MCP
3. If logs exist but errors: Check the payload format and entity type
4. Count LLM calls in agent Lambda - many short calls = tool usage

### Recipe 2: Step Function Never Triggered

**Symptom:** `list-executions` returns empty.

**Check:**
1. Verify Step Function ARN matches what the Lambda/agent sends
2. Check if the triggering Lambda has `states:StartExecution` permission
3. Check the triggering Lambda logs for the StartExecution call
4. Verify the state machine is ACTIVE: `describe-state-machine`

### Recipe 3: Agent Returns Wrong Data

**Symptom:** Agent fetches wrong record or says records exist when they don't.

**Check:**
1. Pull MCP list Lambda logs (`bb-os-mcp-at-list-dev`) for the filter formula
2. Check if filter formula has exact match issues (whitespace, quotes, URL variants)
3. Agent is stateless between Gateway invocations - no session memory
4. Each invocation creates fresh agent instance

### Recipe 4: Timeout Chains

**Symptom:** Agent Lambda times out during a batch operation.

**Check:**
1. Both caller AND callee Lambda timeouts must accommodate the operation
2. Agent Lambda: 600s for batch operations (16+ records)
3. MCP Lambda: 30s per operation (usually sufficient)
4. Step Function: State timeout if configured

### Recipe 5: Lambda Caching Stale Credentials

**Symptom:** Lambda returns "Available aliases: ['default']" but you're passing a different alias, or credentials seem outdated despite updating Secrets Manager.

**Cause:** Warm Lambda containers cache credentials in memory from previous cold starts. Updating a secret doesn't force Lambdas to re-read it.

**Fix:**
1. Verify the secret has the expected structure:
   ```bash
   MSYS_NO_PATHCONV=1 AWS_PROFILE=${PROFILE} aws secretsmanager get-secret-value \
     --secret-id ${SECRET_NAME} --region ${REGION} \
     --query 'SecretString' --output text | python -m json.tool
   ```
2. Force a cold start by updating an environment variable:
   ```bash
   MSYS_NO_PATHCONV=1 AWS_PROFILE=${PROFILE} aws lambda update-function-configuration \
     --function-name ${FUNCTION_NAME} \
     --environment "Variables={...,CACHE_BUST=$(date +%s)}" \
     --region ${REGION}
   ```
3. Wait for the update to propagate:
   ```bash
   MSYS_NO_PATHCONV=1 AWS_PROFILE=${PROFILE} aws lambda wait function-updated \
     --function-name ${FUNCTION_NAME} --region ${REGION}
   ```
4. Re-invoke the Lambda and verify the new credentials are used.

### Recipe 6: Lambda Secrets Manager Access Failure

**Symptom:** Lambda returns "Missing credentials in environment variables" or can't read secrets.

**Check:**
1. Verify the Lambda has the secret name env var set:
   ```bash
   MSYS_NO_PATHCONV=1 AWS_PROFILE=${PROFILE} aws lambda get-function-configuration \
     --function-name ${FUNCTION_NAME} --region ${REGION} \
     --query 'Environment.Variables'
   ```
2. Verify the IAM role has `secretsmanager:GetSecretValue` permission
3. Verify the secret exists and the JSON structure matches what the Lambda expects (check key names, nesting, alias format)
4. If using OAuth tokens: check if the refresh token has expired — re-authenticate via the OAuth flow and update the secret

### Recipe 7: Post-Deployment Lambda Validation

**Symptom:** Lambda behaves differently than expected after deployment, or works in one environment but not another.

**Check:**
1. Compare Lambda configuration:
   ```bash
   MSYS_NO_PATHCONV=1 AWS_PROFILE=${PROFILE} aws lambda get-function-configuration \
     --function-name ${FUNCTION_NAME} --region ${REGION} \
     --query '{Env: Environment.Variables, Timeout: Timeout, Memory: MemorySize, Layers: Layers[].Arn}'
   ```
2. Verify layers are attached and at the correct version
3. Check timeout settings are sufficient for the operation
4. Verify VPC/security group configuration if applicable
5. For systematic post-deployment testing with pytest, use the `dev-writing-integration-tests` skill

---

## Quick Reference: Common Commands

```bash
PROF="PowerUser-398105904466"
REG="us-east-1"

# Recent streams for any Lambda
MSYS_NO_PATHCONV=1 AWS_PROFILE=$PROF aws logs describe-log-streams \
  --log-group-name "/aws/lambda/${FUNC}" \
  --order-by LastEventTime --descending --max-items 3 \
  --region $REG

# Save + parse logs (Windows-safe)
MSYS_NO_PATHCONV=1 AWS_PROFILE=$PROF aws logs get-log-events \
  --log-group-name "/aws/lambda/${FUNC}" \
  --log-stream-name "${STREAM}" \
  --region $REG --limit 200 --output json > "$HOME/logs.json"

# Step Function executions
MSYS_NO_PATHCONV=1 AWS_PROFILE=$PROF aws stepfunctions list-executions \
  --state-machine-arn "${ARN}" --max-results 5 --region $REG

# List ALL Lambdas matching pattern
MSYS_NO_PATHCONV=1 AWS_PROFILE=$PROF aws lambda list-functions \
  --region $REG \
  --query "Functions[?contains(FunctionName, '${PATTERN}')].FunctionName"
```
