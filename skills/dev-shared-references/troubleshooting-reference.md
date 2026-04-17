# Troubleshooting Reference - Known Pitfalls and Cryptic Errors

A reference document of cryptic error messages encountered during development and their actual root causes. Use this to save debugging time.

---

## OAuth / Authentication Errors

### `{"error": "unsupported_grant_type", "error_description": "Invalid grant_type: "}`

**Provider:** Google (and most OAuth providers)

**Root Cause:** Using multipart form data instead of URL-encoded form data for token exchange.

**How it happens:** urllib3's `fields=` parameter sends `multipart/form-data`, but OAuth token endpoints require `application/x-www-form-urlencoded`.

**Wrong code:**
```python
response = http.request("POST", TOKEN_URL, fields=token_data)
```

**Correct code:**
```python
encoded_data = urllib.parse.urlencode(token_data)
response = http.request(
    "POST",
    TOKEN_URL,
    body=encoded_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
```

---

### "No Refresh Token" / `refresh_token` is null

**Provider:** Google

**Root Cause:** The app was already authorized by the user. Google only returns refresh tokens on the FIRST authorization.

**Solution:**
1. Visit https://myaccount.google.com/permissions
2. Find and revoke access for your app
3. Re-authenticate

**Prevention:** Always use `prompt=consent` in the authorization URL to force the consent screen.

---

### `redirect_uri_mismatch`

**Provider:** All OAuth providers

**Root Cause:** The redirect URI in your request doesn't EXACTLY match one registered in the OAuth provider's console.

**Common mistakes:**
- Trailing slash mismatch (`/callback` vs `/callback/`)
- HTTP vs HTTPS
- Different port numbers
- Typos in the path

**Solution:** Copy the exact URL from your API Gateway output and paste it into the provider's console.

---

### `invalid_client`

**Provider:** All OAuth providers

**Root Cause:** Client ID or Client Secret is wrong or for a different environment.

**Check:**
- Are you using dev credentials in prod (or vice versa)?
- Did you copy the full client ID including the `.apps.googleusercontent.com` suffix?
- Is there extra whitespace?

---

## AWS CDK / CloudFormation Errors

### "Export with name X is already exported by stack Y"

**Root Cause:** Two stacks are trying to export the same name.

**Solution:** Use environment-specific export names:
```python
export_name=f"{get_resource_name('my-export')}"  # Includes -dev- or -prod-
```

---

### "Resource handler returned message: null"

**Root Cause:** Usually a Lambda function error during custom resource execution, or an IAM permission issue.

**Debug steps:**
1. Check CloudWatch Logs for the Lambda
2. Look for IAM permission errors
3. Check if the resource already exists

---

### CDK deploy hangs at "Creating CloudFormation changeset"

**Root Cause:** CloudFormation is waiting for a resource that's stuck or the stack is in an inconsistent state.

**Solution:**
1. Check AWS Console for stack status
2. If stuck in `UPDATE_ROLLBACK_COMPLETE`, you may need to delete and recreate
3. Check for circular dependencies between stacks

---

## AWS Lambda Errors

### "Task timed out after X seconds"

**Root Cause:** Lambda didn't complete in time. For OAuth, usually means network call is hanging.

**Common causes:**
- Lambda in VPC without NAT Gateway
- Blocking on a synchronous call that never returns
- Insufficient timeout setting

**Solution:** Increase timeout or add proper error handling with timeouts on HTTP calls.

---

### "Unable to import module 'lambda_function'"

**Root Cause:** The Lambda deployment package structure is wrong.

**Check:**
- Is the handler set correctly? (`lambda_function.lambda_handler` expects `lambda_function.py` at root)
- Are dependencies included?
- Is the file named correctly (case-sensitive on Linux)?

---

## Bash / Deploy Script Errors

### `[: X: integer expression expected`

**Root Cause:** A variable that should be a number contains non-numeric characters or newlines.

**Example that causes this:**
```bash
COUNT=$(grep -c "pattern" file)
if [ "$COUNT" -gt 0 ]; then  # Fails if COUNT has newlines
```

**Solution:** Strip whitespace or use a different comparison:
```bash
if [ "$COUNT" -gt 0 ] 2>/dev/null; then
# Or use arithmetic evaluation:
if (( COUNT > 0 )); then
```

---

### `jq: error: Cannot iterate over null`

**Root Cause:** The JSON path doesn't exist or the JSON is malformed.

**Debug:**
```bash
# See raw output
cat outputs.json | jq '.'

# Use // to provide default
jq -r '.StackName.OutputKey // empty' outputs.json
```

---

### "Permission denied" when running deploy.sh

**Root Cause:** Script doesn't have execute permission.

**Solution:**
```bash
chmod +x deploy.sh
```

---

## Git / Version Control

### "fatal: refusing to merge unrelated histories"

**Root Cause:** Trying to merge two repos that don't share a common ancestor.

**Solution:** Only use if you're sure you want to merge:
```bash
git merge --allow-unrelated-histories
```

---

### "error: Your local changes to the following files would be overwritten"

**Root Cause:** Uncommitted changes conflict with incoming changes.

**Solution:**
```bash
# Stash changes
git stash
git pull
git stash pop

# Or commit first
git add . && git commit -m "WIP"
```

---

## Python / Dependencies

### `protobuf` version conflicts

**Example:**
```
google-ai-generativelanguage requires protobuf<6.0.0dev
but you have protobuf 6.33.5 which is incompatible
```

**Root Cause:** Multiple packages require different versions of a shared dependency.

**Solutions:**
1. Create isolated virtual environments per project
2. Pin a compatible version: `uv add protobuf==5.29.5`
3. Check if newer versions of the conflicting packages resolve it

---

### `ModuleNotFoundError` in Lambda but works locally

**Root Cause:** Dependencies weren't included in deployment package, or layer structure is wrong.

**Check:**
- For layers: Dependencies must be in `python/` subdirectory
- For inline deps: They must be in the zip root alongside your code
- Check that `requirements.txt` was actually installed

---

## Quick Debug Commands

```bash
# Check Lambda logs
aws logs tail /aws/lambda/function-name --follow

# Test Lambda directly
aws lambda invoke --function-name my-function --payload '{}' response.json
cat response.json

# Check secret value
aws secretsmanager get-secret-value --secret-id my-secret | jq -r '.SecretString' | jq '.'

# Verify AWS credentials
aws sts get-caller-identity

# Check stack status
aws cloudformation describe-stacks --stack-name MyStack --query 'Stacks[0].StackStatus'
```
