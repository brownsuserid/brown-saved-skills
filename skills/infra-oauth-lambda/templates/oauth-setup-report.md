# OAuth Infrastructure Setup Report

## Summary

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Provider** | Google / Microsoft / Slack / GitHub |
| **Environment** | dev / staging / prod |
| **AWS Profile** | Profile used |
| **Region** | us-east-1 / etc |
| **Status** | Deployed / Pending provider config / Tested |

## Infrastructure Deployed

| Resource | Name | ARN/URL |
|----------|------|---------|
| HTTP API Gateway | resource-prefix-oauth-api | https://{api-id}.execute-api.{region}.amazonaws.com |
| Lambda Function | resource-prefix-oauth-callback | arn:aws:lambda:... |
| Secrets Manager Secret | resource-prefix-credentials | arn:aws:secretsmanager:... |
| IAM Role | resource-prefix-oauth-lambda-role | arn:aws:iam:... |

## OAuth Flow URLs

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Instructions | https://{api-url}/oauth | Landing page with setup info |
| Start OAuth | https://{api-url}/oauth/start | Redirects to provider consent screen |
| Callback | https://{api-url}/oauth/callback | Receives auth code from provider |

## Provider Configuration

### Required Console Setup

| Setting | Value | Status |
|---------|-------|--------|
| Redirect URI | https://{api-url}/oauth/callback | Configured / Pending |
| Client ID | Set in Lambda env vars | Configured / Pending |
| Client Secret | Set in Lambda env vars | Configured / Pending |
| Required Scopes | (list scopes) | Enabled / Pending |

### Provider Console URL

(Link to the provider's developer console)

## Lambda Environment Variables

| Variable | Value | Source |
|----------|-------|--------|
| ENVIRONMENT | dev | CDK |
| CREDENTIALS_SECRET | secret-name | CDK |
| OAUTH_CLIENT_ID | (configured) | Deploy script |
| OAUTH_CLIENT_SECRET | (configured) | Deploy script |
| OAUTH_REDIRECT_URI | https://{api-url}/oauth/callback | CDK (auto-computed) |

## Security Checklist

- [ ] Client secret stored securely (env var from deploy script, not hardcoded)
- [ ] Secrets Manager secret has restricted IAM access
- [ ] CORS restricted or removed (OAuth redirects don't need CORS)
- [ ] Lambda logs do not contain tokens or auth codes
- [ ] HTTPS-only (enforced by API Gateway by default)

## Testing

### Test Steps

1. Visit the OAuth start URL in a browser
2. Complete provider consent screen
3. Verify redirect back to callback URL
4. Check success page shows email-based alias
5. Verify credentials in Secrets Manager: `aws secretsmanager get-secret-value --secret-id <secret-name>`

### Test Results

| Step | Result | Notes |
|------|--------|-------|
| Start redirect | Pass/Fail | |
| Provider consent | Pass/Fail | |
| Callback token exchange | Pass/Fail | |
| Credentials saved | Pass/Fail | |
| Email auto-naming | Pass/Fail | |

## Accounts Configured

| Email/Alias | Date Added | Status |
|-------------|-----------|--------|
| user@example.com | YYYY-MM-DD | Active |

## Troubleshooting Reference

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `unsupported_grant_type` | multipart instead of URL-encoded | Fix token exchange to use `body=urllib.parse.urlencode(data)` |
| No refresh token | App already authorized | Revoke at provider permissions page, re-authorize |
| `redirect_uri_mismatch` | URI not registered in console | Add exact callback URL to provider console |
| `invalid_client` | Wrong client ID/secret | Check Lambda env vars match provider console |
| 403 on userinfo | Missing scope | Add userinfo.email (Google) or User.Read (Microsoft) |
