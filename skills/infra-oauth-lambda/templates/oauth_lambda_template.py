"""
OAuth Callback Lambda Template - Collects OAuth credentials via browser flow.

This Lambda handles a web-based OAuth flow:
1. User visits the /oauth/start endpoint
2. Lambda redirects to OAuth provider consent screen
3. User authenticates with provider
4. Provider redirects back to /oauth/callback with auth code
5. Lambda exchanges code for tokens and stores in Secrets Manager

CUSTOMIZATION POINTS (marked with # CUSTOMIZE):
- SCOPES: Add/remove OAuth scopes for your use case
- Provider URLs: Change for Microsoft, Slack, etc.
- Credential storage format: Modify what gets saved

Environment Variables:
    CREDENTIALS_SECRET: Name of the Secrets Manager secret
    OAUTH_CLIENT_ID: OAuth client ID from provider console
    OAUTH_CLIENT_SECRET: OAuth client secret from provider console
    OAUTH_REDIRECT_URI: The callback URL (API Gateway endpoint)
    ENVIRONMENT: dev or prod
"""

import json
import logging
import os
import urllib.parse
from typing import Any

import boto3
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# =============================================================================
# CUSTOMIZE: OAuth Configuration
# =============================================================================
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",  # For auto-naming by email
]

# CUSTOMIZE: Provider endpoints (these are for Google)
OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# =============================================================================
# Helper Functions
# =============================================================================


def get_env_var(name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_redirect_response(url: str) -> dict[str, Any]:
    """Build an HTTP 302 redirect response."""
    return {
        "statusCode": 302,
        "headers": {
            "Location": url,
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
        "body": "",
    }


def build_html_response(
    status_code: int, title: str, message: str, details: str = ""
) -> dict[str, Any]:
    """Build an HTML response for browser display."""
    success_class = "success" if status_code == 200 else "error"
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; }}
        .success {{ color: #28a745; }}
        .error {{ color: #dc3545; }}
        .details {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="{success_class}">{title}</h1>
        <p>{message}</p>
        {f'<div class="details">{details}</div>' if details else ""}
    </div>
</body>
</html>"""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html"},
        "body": html,
    }


# =============================================================================
# Route Handlers
# =============================================================================


def handle_start(event: dict[str, Any]) -> dict[str, Any]:
    """Handle /oauth/start - Redirect to OAuth provider consent screen."""
    logger.info("Starting OAuth flow")

    try:
        client_id = get_env_var("OAUTH_CLIENT_ID")
        redirect_uri = get_env_var("OAUTH_REDIRECT_URI")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return build_html_response(
            500,
            "Configuration Error",
            str(e),
            "Please ensure OAUTH_CLIENT_ID and OAUTH_REDIRECT_URI are set.",
        )

    # Get optional alias from query string (fallback, email preferred)
    query_params = event.get("queryStringParameters") or {}
    alias = query_params.get("alias", "default")

    # Build OAuth authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Force consent to get refresh token
        "state": alias,  # Pass alias through state parameter
    }
    auth_url = f"{OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    logger.info(f"Redirecting to OAuth provider for alias: {alias}")
    return build_redirect_response(auth_url)


def handle_callback(event: dict[str, Any]) -> dict[str, Any]:
    """Handle /oauth/callback - Exchange code for tokens and store."""
    logger.info("Processing OAuth callback")

    query_params = event.get("queryStringParameters") or {}

    # Check for errors from provider
    if "error" in query_params:
        error = query_params.get("error", "unknown")
        error_desc = query_params.get("error_description", "No description")
        logger.error(f"OAuth error: {error} - {error_desc}")
        return build_html_response(
            400,
            "Authentication Failed",
            f"Provider returned an error: {error}",
            error_desc,
        )

    # Get authorization code
    code = query_params.get("code")
    if not code:
        logger.error("No authorization code in callback")
        return build_html_response(
            400,
            "Missing Authorization Code",
            "The callback did not include an authorization code.",
        )

    try:
        client_id = get_env_var("OAUTH_CLIENT_ID")
        client_secret = get_env_var("OAUTH_CLIENT_SECRET")
        redirect_uri = get_env_var("OAUTH_REDIRECT_URI")
        secret_name = get_env_var("CREDENTIALS_SECRET")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return build_html_response(500, "Configuration Error", str(e))

    # ==========================================================================
    # CRITICAL: Token Exchange - Use URL-encoded form data, NOT multipart!
    # ==========================================================================
    logger.info("Exchanging authorization code for tokens")
    http = urllib3.PoolManager()

    token_data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    # URL-encode the data as application/x-www-form-urlencoded
    # DO NOT use fields= parameter - it sends multipart which providers reject!
    encoded_data = urllib.parse.urlencode(token_data)

    try:
        response = http.request(
            "POST",
            OAUTH_TOKEN_URL,
            body=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status != 200:
            error_data = json.loads(response.data.decode("utf-8"))
            logger.error(f"Token exchange failed: {error_data}")
            return build_html_response(
                500,
                "Token Exchange Failed",
                "Failed to exchange authorization code for tokens.",
                json.dumps(error_data, indent=2),
            )

        token_response = json.loads(response.data.decode("utf-8"))
        logger.info("Successfully obtained tokens")

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        return build_html_response(
            500,
            "Token Exchange Error",
            f"An error occurred during token exchange: {e}",
        )

    # Extract credentials
    refresh_token = token_response.get("refresh_token")
    access_token = token_response.get("access_token")

    if not refresh_token:
        logger.warning("No refresh token in response - user may have already authorized")
        return build_html_response(
            400,
            "No Refresh Token",
            "Provider did not return a refresh token. "
            "This usually means the app was already authorized.",
            "Revoke access in your account settings, then try again.",
        )

    # Get user's email address to use as alias (auto-naming)
    alias = query_params.get("state", "default")  # Fallback to state parameter

    if access_token:
        try:
            logger.info("Fetching user email from userinfo API")
            userinfo_response = http.request(
                "GET",
                OAUTH_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status == 200:
                userinfo = json.loads(userinfo_response.data.decode("utf-8"))
                email = userinfo.get("email")
                if email:
                    alias = email
                    logger.info(f"Using email as alias: {alias}")
                else:
                    logger.warning("No email in userinfo response, using state parameter")
            else:
                logger.warning(f"Failed to get userinfo: {userinfo_response.status}")
        except Exception as e:
            logger.warning(f"Error fetching userinfo: {e}, using state parameter as alias")

    # Get existing credentials from Secrets Manager
    secretsmanager = boto3.client("secretsmanager")

    try:
        existing_secret = secretsmanager.get_secret_value(SecretId=secret_name)
        credentials_store = json.loads(existing_secret["SecretString"])
        logger.info(f"Loaded existing credentials with aliases: {list(credentials_store.keys())}")
    except secretsmanager.exceptions.ResourceNotFoundException:
        logger.info("No existing credentials found, starting fresh")
        credentials_store = {}
    except json.JSONDecodeError:
        logger.warning("Existing secret was not valid JSON, starting fresh")
        credentials_store = {}

    # CUSTOMIZE: Credential storage format
    credentials_store[alias] = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # Save to Secrets Manager
    try:
        secretsmanager.put_secret_value(
            SecretId=secret_name,
            SecretString=json.dumps(credentials_store, indent=2),
        )
        logger.info(f"Saved credentials for alias '{alias}' to Secrets Manager")
    except Exception as e:
        logger.error(f"Failed to save to Secrets Manager: {e}")
        return build_html_response(
            500,
            "Failed to Save Credentials",
            f"Could not save credentials to Secrets Manager: {e}",
        )

    # Success!
    env = os.environ.get("ENVIRONMENT", "unknown")
    return build_html_response(
        200,
        "Credentials Saved Successfully!",
        f"OAuth credentials for '{alias}' have been saved to AWS Secrets Manager.",
        f"Environment: {env.upper()}<br>"
        f"Secret: {secret_name}<br>"
        f"Aliases configured: {', '.join(credentials_store.keys())}",
    )


def handle_instructions(event: dict[str, Any]) -> dict[str, Any]:
    """Handle /oauth - Show instructions page."""
    env = os.environ.get("ENVIRONMENT", "unknown")
    base_url = event.get("requestContext", {}).get("domainName", "")
    stage = event.get("requestContext", {}).get("stage", "")

    if base_url and stage:
        start_url = f"https://{base_url}/{stage}/oauth/start"
    else:
        start_url = "/oauth/start"

    return build_html_response(
        200,
        f"OAuth Setup ({env.upper()})",
        "Use this service to configure OAuth credentials.",
        f'<a href="{start_url}">Click here to start OAuth flow</a><br><br>'
        f"Credentials will be automatically named by your email address.",
    )


# =============================================================================
# Main Handler
# =============================================================================


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Main Lambda handler - routes to appropriate handler based on path."""
    # Log path only — avoid logging full event which may contain auth codes
    path = event.get("rawPath", "") or event.get("path", "")
    logger.info(f"OAuth handler invoked for path: {path}")

    # Get the path from the event
    path = event.get("rawPath", "") or event.get("path", "")

    # Route based on path
    if "/start" in path:
        return handle_start(event)
    elif "/callback" in path:
        return handle_callback(event)
    else:
        return handle_instructions(event)
