# OAuth Provider Endpoints Reference

Quick reference for OAuth 2.0 endpoints and configuration for common providers.

## Google

### Endpoints
```
Authorization: https://accounts.google.com/o/oauth2/v2/auth
Token:         https://oauth2.googleapis.com/token
Userinfo:      https://www.googleapis.com/oauth2/v2/userinfo
Revoke:        https://oauth2.googleapis.com/revoke
```

### Common Scopes
| Scope | Description |
|-------|-------------|
| `https://www.googleapis.com/auth/gmail.send` | Send emails |
| `https://www.googleapis.com/auth/gmail.readonly` | Read emails |
| `https://www.googleapis.com/auth/gmail.modify` | Read/write emails |
| `https://www.googleapis.com/auth/userinfo.email` | Get user's email |
| `https://www.googleapis.com/auth/userinfo.profile` | Get user's profile |
| `https://www.googleapis.com/auth/drive.readonly` | Read Drive files |
| `https://www.googleapis.com/auth/calendar.readonly` | Read calendar |

### Required Parameters
```python
params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": " ".join(SCOPES),
    "access_type": "offline",      # Required for refresh token
    "prompt": "consent",           # Force consent for refresh token
    "state": custom_state,         # Optional, passed back in callback
}
```

### Console URL
https://console.cloud.google.com/apis/credentials

---

## Microsoft (Azure AD)

### Endpoints
```
Authorization: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
Token:         https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Userinfo:      https://graph.microsoft.com/v1.0/me
```

**Tenant Values:**
- `common` - Any Microsoft account
- `organizations` - Work/school accounts only
- `consumers` - Personal accounts only
- `{tenant-id}` - Specific tenant

### Common Scopes
| Scope | Description |
|-------|-------------|
| `Mail.Send` | Send emails |
| `Mail.Read` | Read emails |
| `User.Read` | Read user profile |
| `Calendars.Read` | Read calendar |
| `Files.Read` | Read OneDrive files |
| `offline_access` | Get refresh token |

### Required Parameters
```python
params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": " ".join(SCOPES),
    "response_mode": "query",
    "state": custom_state,
}
```

### Console URL
https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade

---

## Slack

### Endpoints
```
Authorization: https://slack.com/oauth/v2/authorize
Token:         https://slack.com/api/oauth.v2.access
```

### Common Scopes (Bot)
| Scope | Description |
|-------|-------------|
| `chat:write` | Post messages |
| `channels:read` | View channels |
| `users:read` | View users |
| `files:write` | Upload files |

### Required Parameters
```python
params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "scope": ",".join(SCOPES),  # Comma-separated for Slack!
    "state": custom_state,
}
```

### Console URL
https://api.slack.com/apps

---

## GitHub

### Endpoints
```
Authorization: https://github.com/login/oauth/authorize
Token:         https://github.com/login/oauth/access_token
Userinfo:      https://api.github.com/user
```

### Common Scopes
| Scope | Description |
|-------|-------------|
| `repo` | Full repository access |
| `read:user` | Read user profile |
| `user:email` | Read user email |
| `workflow` | Update GitHub Actions |

### Console URL
https://github.com/settings/developers

---

## Token Exchange Format

**ALL providers require `application/x-www-form-urlencoded`:**

```python
import urllib.parse
import urllib3

token_data = {
    "code": code,
    "client_id": client_id,
    "client_secret": client_secret,
    "redirect_uri": redirect_uri,
    "grant_type": "authorization_code",
}

# CORRECT
encoded_data = urllib.parse.urlencode(token_data)
response = http.request(
    "POST",
    TOKEN_URL,
    body=encoded_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

# WRONG - DO NOT USE fields= parameter
response = http.request("POST", TOKEN_URL, fields=token_data)  # Sends multipart!
```

---

## Common Errors

| Error | Provider | Cause | Solution |
|-------|----------|-------|----------|
| `invalid_grant` | All | Code expired or already used | Restart OAuth flow |
| `unsupported_grant_type` | Google | Wrong Content-Type | Use URL-encoded, not multipart |
| `redirect_uri_mismatch` | All | URI not registered | Add exact URI to console |
| `invalid_client` | All | Wrong client ID/secret | Check credentials |
| No refresh token | Google | Already authorized | Revoke and re-authorize |

---

## Revocation URLs

To force re-authorization (needed to get new refresh token):

| Provider | URL |
|----------|-----|
| Google | https://myaccount.google.com/permissions |
| Microsoft | https://account.live.com/consent/Manage |
| Slack | https://slack.com/apps/manage |
| GitHub | https://github.com/settings/applications |
