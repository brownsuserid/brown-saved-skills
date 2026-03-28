---
name: infra-oauth-lambda
description: Creates browser-based OAuth credential collection flows running in AWS Lambda + API Gateway when implementing OAuth integrations. Credentials are automatically saved to AWS Secrets Manager. Use this skill whenever the user needs to set up OAuth for Google, Microsoft, Slack, GitHub, or any OAuth 2.0 provider in a serverless AWS environment. Also triggers for "collect credentials via browser", "self-service OAuth", "token exchange Lambda", "store refresh tokens in Secrets Manager", or when someone is getting `unsupported_grant_type` errors from an OAuth token exchange. Do NOT use for general API authentication, API keys, Cognito user pools, or non-OAuth credential management.
---

# Serverless OAuth Lambda Skill

Create browser-based OAuth credential collection flows hosted entirely in AWS. Users visit a URL, authenticate with an OAuth provider, and credentials are automatically saved to Secrets Manager.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser   │────▶│  API Gateway     │────▶│  OAuth Lambda   │
│             │     │  (HTTP API)      │     │                 │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                    ┌──────────────────┐               │
                    │  OAuth Provider  │◀──────────────┤
                    │  (Google, etc.)  │               │
                    └──────────────────┘               │
                                                       ▼
                                             ┌─────────────────┐
                                             │ Secrets Manager │
                                             │ (credentials)   │
                                             └─────────────────┘
```

**Flow:** User visits `/oauth/start` → browser redirects to provider consent screen → user authenticates → provider redirects back to `/oauth/callback` with auth code → Lambda exchanges code for tokens and saves to Secrets Manager → user sees success page.

## When to Use This Skill

- Collecting OAuth credentials without requiring users to run local scripts
- Supporting multiple accounts/aliases stored in a single Secrets Manager secret
- Creating self-service credential management for production environments
- Integrating with any OAuth 2.0 provider (Google, Microsoft, Slack, GitHub, etc.)
- Debugging `unsupported_grant_type` or `invalid_grant` errors in OAuth token exchange

## Process

Use the TodoWrite tool to track progress through these phases.

---

## Phase 1: Understand Provider Requirements

Determine the OAuth provider and gather endpoint details. Read `references/oauth-provider-endpoints.md` for provider-specific endpoints, scopes, and parameters.

### Key Differences by Provider

| Provider | Refresh Token Mechanism | Scope Separator | Userinfo Endpoint |
|----------|------------------------|-----------------|-------------------|
| Google | `access_type=offline` + `prompt=consent` | Space | googleapis.com/oauth2/v2/userinfo |
| Microsoft | `offline_access` scope | Space | graph.microsoft.com/v1.0/me |
| Slack | Automatic with bot tokens | **Comma** | N/A (token response includes team info) |
| GitHub | N/A (tokens don't expire) | Space | api.github.com/user |

---

## Phase 2: Create Lambda Handler

Create the OAuth callback Lambda with three routes:
- `/oauth` — Instructions page
- `/oauth/start` — Redirect to OAuth provider
- `/oauth/callback` — Exchange code for tokens

Use the template at `templates/oauth_lambda_template.py` as a starting point. Adapt the provider endpoints, scopes, and userinfo URL for the target provider.

### Critical: Token Exchange Format

**This is the #1 source of bugs.** All OAuth providers require `application/x-www-form-urlencoded` for token exchange. Using multipart/form-data (which urllib3's `fields=` parameter sends) will fail silently with a confusing error.

```python
# CORRECT — URL-encoded form data
import urllib.parse
import urllib3

token_data = {
    "code": code,
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": redirect_uri,
    "grant_type": "authorization_code",
}
encoded_data = urllib.parse.urlencode(token_data)

http = urllib3.PoolManager()
response = http.request(
    "POST",
    TOKEN_URL,
    body=encoded_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

# WRONG — urllib3 fields= sends multipart/form-data which providers reject
response = http.request("POST", url, fields=token_data)  # WILL FAIL!
```

**Error you'll see if wrong:** `{"error": "unsupported_grant_type", "error_description": "Invalid grant_type: "}`

---

## Phase 3: Create CDK Infrastructure

Use the template at `templates/oauth_cdk_construct.py`. Key requirements:

1. **HTTP API Gateway** (not REST API) — simpler, cheaper, supports Lambda proxy
2. **Separate IAM role** with Secrets Manager read AND write access
3. **No CORS needed** — OAuth uses browser redirects, not XHR

```python
# Grant BOTH read and write — write is needed to save credentials
secret.grant_read(oauth_lambda_role)
secret.grant_write(oauth_lambda_role)  # Easy to forget!
```

---

## Phase 4: Configure OAuth Provider

After deployment, configure the provider's developer console:

1. Create OAuth client credentials (Web application type)
2. Add authorized redirect URI: `https://{api-id}.execute-api.{region}.amazonaws.com/oauth/callback`
3. Copy Client ID and Client Secret to deploy script or env file

### Lambda Environment Variables

Set these via deploy script (not hardcoded in CDK):

| Variable | Source |
|----------|--------|
| `OAUTH_CLIENT_ID` | Provider console |
| `OAUTH_CLIENT_SECRET` | Provider console |
| `OAUTH_REDIRECT_URI` | CDK output (auto-computed) |
| `CREDENTIALS_SECRET` | CDK (secret name) |
| `ENVIRONMENT` | CDK (dev/prod) |

---

## Phase 5: Multi-Account Credential Storage

Store multiple accounts in a single Secrets Manager secret as JSON, keyed by email:

```json
{
  "user@gmail.com": {
    "refresh_token": "1//xxxxx",
    "client_id": "xxxxx.apps.googleusercontent.com",
    "client_secret": "GOCSPX-xxxxx"
  },
  "sales@company.com": {
    "refresh_token": "1//yyyyy",
    "client_id": "xxxxx.apps.googleusercontent.com",
    "client_secret": "GOCSPX-xxxxx"
  }
}
```

Request the userinfo email scope and fetch the user's email after token exchange to auto-name credentials. This avoids manual alias management.

---

## Phase 6: Deploy Script Integration

The deploy script should:
1. Deploy CDK infrastructure
2. Read OAuth client credentials from env file
3. Update Lambda environment variables post-deploy

```bash
aws lambda update-function-configuration \
    --function-name "$OAUTH_LAMBDA_NAME" \
    --environment "Variables={OAUTH_CLIENT_ID=$CLIENT_ID,...}" \
    --region "$REGION" \
    --profile "$PROFILE"
```

---

## Phase 7: Validate Setup

Run the scanner to verify the implementation:

```bash
python scripts/scan_oauth_infrastructure.py <path-to-project>
```

The scanner checks for the common token exchange bug, Secrets Manager permissions, CORS configuration, sensitive data logging, and other issues.

Use the report template at `templates/oauth-setup-report.md` to document the deployed infrastructure, URLs, and remaining manual steps.

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid grant_type: ` | multipart instead of URL-encoded | Use `body=urllib.parse.urlencode(data)` with Content-Type header |
| No refresh token | App already authorized | Revoke at provider permissions page, re-authorize |
| `redirect_uri_mismatch` | Callback URL not registered | Add exact URL to provider console |
| 403 on userinfo | Missing scope | Add userinfo.email (Google) or User.Read (Microsoft) |
| `invalid_client` | Wrong credentials | Check Lambda env vars match provider console |

---

## Security Considerations

- **Client secrets in env vars**: Deploy script sets these post-deploy; they're not in CDK source code. Consider migrating to Secrets Manager for client secrets too.
- **No CORS needed**: OAuth flows use browser redirects, not XHR. Remove CORS or restrict tightly.
- **Avoid logging sensitive data**: Don't log the full Lambda event (contains auth codes) or token responses. Log paths and status codes only.
- **HTTPS enforced**: API Gateway endpoints are HTTPS-only by default.
- **State parameter**: Currently used for alias passing. For production, consider adding CSRF protection by signing the state value.

---

## Checklist

**Lambda Handler:**
- [ ] URL-encoded form data for token exchange (`body=urllib.parse.urlencode()`)
- [ ] Explicit `Content-Type: application/x-www-form-urlencoded` header
- [ ] Handles `/oauth`, `/oauth/start`, `/oauth/callback` routes
- [ ] Fetches email for auto-naming aliases
- [ ] Returns HTML responses for browser display
- [ ] No sensitive data (tokens, auth codes) in logs

**CDK Infrastructure:**
- [ ] HTTP API Gateway (not REST)
- [ ] Separate IAM role for OAuth Lambda
- [ ] Secrets Manager read AND write permission granted
- [ ] No overly permissive CORS
- [ ] Environment-specific naming

**Deploy Script:**
- [ ] Reads OAuth credentials from env file
- [ ] Updates Lambda env vars after deploy
- [ ] Displays OAuth URL in summary

**Provider Console:**
- [ ] Redirect URI configured with exact callback URL
- [ ] Required scopes enabled
- [ ] Client ID/Secret in env file

---

## Files in This Skill

```
infra-oauth-lambda/
├── SKILL.md                              # This file
├── evals/
│   └── evals.json                        # Evaluation scenarios
├── scripts/
│   └── scan_oauth_infrastructure.py      # Infrastructure scanner
├── templates/
│   ├── oauth_lambda_template.py          # Lambda handler template (Google default)
│   ├── oauth_cdk_construct.py            # CDK construct template
│   └── oauth-setup-report.md             # Post-setup documentation template
└── references/
    └── oauth-provider-endpoints.md       # Provider endpoints, scopes, quirks
```

---

## Related Skills

- `infra-cdk-quality` — Deploy script patterns for post-deploy Lambda configuration (Phase 7)
- `infra-cdk-quality` — CDK best practices and security scanning
