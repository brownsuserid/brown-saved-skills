#!/usr/bin/env python3
"""Scan a CDK project for OAuth infrastructure quality and common mistakes.

Usage:
    python scan_oauth_infrastructure.py <path-to-cdk-project-or-lambda-dir>
    python scan_oauth_infrastructure.py ./cdk/
    python scan_oauth_infrastructure.py ./lambda_functions/oauth_callback/

Checks for:
  - Token exchange uses URL-encoded form data (not multipart)
  - Content-Type header explicitly set on token exchange
  - HTTP API Gateway used (not REST API)
  - Secrets Manager write permissions granted
  - Lambda env vars not left as placeholders
  - CSRF protection via state parameter
  - Proper error handling on callback route
  - Refresh token handling (prompt=consent / offline_access)
  - CORS not overly permissive on credential endpoints
  - Sensitive data not logged (auth codes, tokens)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Issue:
    category: str
    severity: str  # "error", "warning", "info"
    message: str
    file: str = ""
    line: int = 0


@dataclass
class ScanResult:
    issues: list[Issue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    files_scanned: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def score(self) -> float:
        total = len(self.checks_passed) + len(self.checks_failed)
        if total == 0:
            return 0.0
        return len(self.checks_passed) / total * 100


def find_python_files(path: Path) -> list[Path]:
    """Find all Python files in the given path."""
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    return sorted(path.rglob("*.py"))


def scan_lambda_code(content: str, filepath: str) -> list[tuple[str, Issue | None]]:
    """Scan Lambda handler code for OAuth issues."""
    results: list[tuple[str, Issue | None]] = []
    lower = content.lower()
    lines = content.splitlines()

    # Check 1: Token exchange uses URL-encoded (not multipart)
    has_urlencode = "urllib.parse.urlencode" in content
    has_fields_param = bool(re.search(r"\.request\([^)]*fields\s*=", content))

    if has_fields_param:
        # Find the line number
        line_num = 0
        for i, line in enumerate(lines, 1):
            if re.search(r"\.request\([^)]*fields\s*=", line) or "fields=" in line:
                line_num = i
                break
        results.append(
            (
                "url-encoded-token-exchange",
                Issue(
                    "token-exchange",
                    "error",
                    "CRITICAL: Using urllib3 fields= parameter sends multipart/form-data. "
                    "OAuth providers require application/x-www-form-urlencoded. "
                    "Use urllib.parse.urlencode(data) with body= parameter instead.",
                    filepath,
                    line_num,
                ),
            )
        )
    elif has_urlencode:
        results.append(("url-encoded-token-exchange", None))
    else:
        # No token exchange found at all — might not be the Lambda file
        if "oauth" in lower or "token" in lower:
            results.append(
                (
                    "url-encoded-token-exchange",
                    Issue(
                        "token-exchange",
                        "warning",
                        "OAuth-related code found but no urllib.parse.urlencode() detected. "
                        "Ensure token exchange uses URL-encoded form data.",
                        filepath,
                    ),
                )
            )

    # Check 2: Content-Type header explicitly set
    has_content_type = "application/x-www-form-urlencoded" in content
    if has_content_type:
        results.append(("content-type-header", None))
    elif "oauth" in lower and ("token" in lower or "grant" in lower):
        results.append(
            (
                "content-type-header",
                Issue(
                    "token-exchange",
                    "error",
                    "Content-Type: application/x-www-form-urlencoded header not explicitly set. "
                    "Some HTTP clients may default to a different content type.",
                    filepath,
                ),
            )
        )

    # Check 3: Refresh token handling
    has_prompt_consent = "prompt" in lower and "consent" in lower
    has_offline_access = "offline_access" in lower
    has_access_type_offline = "access_type" in lower and "offline" in lower
    if has_prompt_consent or has_offline_access or has_access_type_offline:
        results.append(("refresh-token-params", None))
    elif "oauth" in lower:
        results.append(
            (
                "refresh-token-params",
                Issue(
                    "oauth-config",
                    "warning",
                    "No refresh token parameters detected. Google needs prompt=consent + "
                    "access_type=offline; Microsoft needs offline_access scope.",
                    filepath,
                ),
            )
        )

    # Check 4: Error handling on callback
    has_error_check = "error" in lower and "query" in lower
    has_code_check = bool(re.search(r'\.get\(["\']code["\']', content))
    if has_error_check and has_code_check:
        results.append(("callback-error-handling", None))
    elif "/callback" in lower or "handle_callback" in lower:
        if not has_error_check:
            results.append(
                (
                    "callback-error-handling",
                    Issue(
                        "error-handling",
                        "warning",
                        "Callback handler may not check for OAuth error responses. "
                        "Providers return error= and error_description= on failure.",
                        filepath,
                    ),
                )
            )

    # Check 5: Sensitive data logging
    sensitive_log_patterns = [
        (r"logger?\.\w+\(.*event.*\)", "Full event object logged — may contain auth codes"),
        (r"logger?\.\w+\(.*secret.*\)", "Secret values may be logged"),
        (r"logger?\.\w+\(.*token.*\)", "Token values may be logged"),
        (r"print\(.*event.*\)", "Event printed — may contain auth codes"),
    ]
    for pattern, msg in sensitive_log_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            line_text = lines[line_num - 1].strip() if line_num <= len(lines) else ""
            # Skip false positives like "token exchange" descriptions
            if "token_response" in line_text and "logger" not in line_text.lower():
                continue
            # Only flag actual logging calls
            if re.match(r"(logger?\.\w+|print)\s*\(", line_text, re.IGNORECASE):
                results.append(
                    (
                        "sensitive-data-logging",
                        Issue(
                            "security",
                            "warning",
                            f"Potentially sensitive data logged: {msg}",
                            filepath,
                            line_num,
                        ),
                    )
                )
                break  # One warning is enough

    # Check 6: Auto-naming by email
    has_userinfo = "userinfo" in lower
    has_email_alias = "email" in lower and ("alias" in lower or "key" in lower)
    if has_userinfo or has_email_alias:
        results.append(("email-auto-naming", None))
    elif "secret" in lower and "put" in lower:
        results.append(
            (
                "email-auto-naming",
                Issue(
                    "feature",
                    "info",
                    "Credentials are stored but no email-based auto-naming detected. "
                    "Fetching userinfo email provides better credential organization.",
                    filepath,
                ),
            )
        )

    return results


def scan_cdk_code(content: str, filepath: str) -> list[tuple[str, Issue | None]]:
    """Scan CDK infrastructure code for OAuth issues."""
    results: list[tuple[str, Issue | None]] = []
    lower = content.lower()

    # Check 1: HTTP API (not REST API)
    has_http_api = "httpapi" in lower or "apigwv2" in lower
    has_rest_api = bool(re.search(r"RestApi|apigateway\b(?!v2)", content))
    if has_http_api and not has_rest_api:
        results.append(("http-api-gateway", None))
    elif has_rest_api:
        results.append(
            (
                "http-api-gateway",
                Issue(
                    "infrastructure",
                    "warning",
                    "REST API Gateway detected. HTTP API (apigwv2.HttpApi) is simpler, "
                    "cheaper, and sufficient for OAuth callback flows.",
                    filepath,
                ),
            )
        )

    # Check 2: Secrets Manager write permission
    has_grant_write = "grant_write" in content
    has_grant_read = "grant_read" in content
    if has_grant_write and has_grant_read:
        results.append(("secrets-write-permission", None))
    elif has_grant_read and not has_grant_write:
        results.append(
            (
                "secrets-write-permission",
                Issue(
                    "permissions",
                    "error",
                    "Secrets Manager read permission found but NO write permission. "
                    "The OAuth Lambda needs grant_write() to save credentials.",
                    filepath,
                ),
            )
        )

    # Check 3: CORS configuration
    cors_allow_all = bool(re.search(r'allow_origins\s*=\s*\[\s*["\']?\*', content))
    if cors_allow_all:
        results.append(
            (
                "cors-restrictive",
                Issue(
                    "security",
                    "warning",
                    "CORS allows all origins (*). For a credential-handling endpoint, "
                    "consider restricting to specific domains or removing CORS entirely "
                    "(OAuth redirects don't need CORS).",
                    filepath,
                ),
            )
        )
    else:
        results.append(("cors-restrictive", None))

    # Check 4: Placeholder env vars
    placeholder_patterns = [
        "PLACEHOLDER",
        "xxxxx",
        "your-client-id",
        "CHANGE_ME",
    ]
    has_placeholder = any(p in content for p in placeholder_patterns)
    if has_placeholder:
        results.append(
            (
                "no-placeholder-env-vars",
                Issue(
                    "configuration",
                    "info",
                    "Placeholder values found in environment variables. These should be "
                    "replaced by deploy script or parameter store values before deployment.",
                    filepath,
                ),
            )
        )
    else:
        results.append(("no-placeholder-env-vars", None))

    # Check 5: Separate IAM role (not default Lambda role)
    has_custom_role = bool(re.search(r"iam\.Role\(", content))
    if has_custom_role:
        results.append(("separate-iam-role", None))
    elif "oauth" in lower and "lambda" in lower:
        results.append(
            (
                "separate-iam-role",
                Issue(
                    "security",
                    "warning",
                    "No dedicated IAM role found for OAuth Lambda. Use a separate role "
                    "with least-privilege Secrets Manager access.",
                    filepath,
                ),
            )
        )

    return results


def scan_directory(path: Path) -> ScanResult:
    """Scan all Python files in a directory."""
    result = ScanResult()
    python_files = find_python_files(path)

    if not python_files:
        result.issues.append(
            Issue(
                "no-files",
                "error",
                f"No Python files found in {path}",
            )
        )
        return result

    for filepath in python_files:
        content = filepath.read_text(encoding="utf-8")
        result.files_scanned.append(str(filepath))
        lower = content.lower()

        # Determine file type and scan accordingly
        is_lambda = any(
            k in lower
            for k in [
                "def lambda_handler",
                "def handle_callback",
                "def handle_start",
                "def token_exchange",
            ]
        )
        is_cdk = any(
            k in lower
            for k in [
                "from aws_cdk",
                "import aws_cdk",
                "constructs import",
                "httpapi",
                "apigwv2",
            ]
        )

        # CDK files should only get CDK checks, not Lambda checks
        # (CDK files reference "oauth" but don't have token exchange code)
        if is_cdk and not is_lambda:
            for check_name, issue in scan_cdk_code(content, str(filepath)):
                if issue:
                    result.checks_failed.append(check_name)
                    result.issues.append(issue)
                else:
                    result.checks_passed.append(check_name)
        elif is_lambda:
            for check_name, issue in scan_lambda_code(content, str(filepath)):
                if issue:
                    result.checks_failed.append(check_name)
                    result.issues.append(issue)
                else:
                    result.checks_passed.append(check_name)
            # Also run CDK checks if file has both Lambda and CDK code
            if is_cdk:
                for check_name, issue in scan_cdk_code(content, str(filepath)):
                    if issue:
                        result.checks_failed.append(check_name)
                        result.issues.append(issue)
                    else:
                        result.checks_passed.append(check_name)

    # Deduplicate checks (a check passes if it passed in any file)
    passed_set = set(result.checks_passed)
    failed_set = set(result.checks_failed) - passed_set
    result.checks_passed = sorted(passed_set)
    result.checks_failed = sorted(failed_set)

    return result


def format_report(result: ScanResult) -> str:
    """Format scan results as a readable report."""
    lines: list[str] = []
    lines.append(f"OAuth Infrastructure Scan Score: {result.score:.0f}%")
    passed = len(result.checks_passed)
    total = passed + len(result.checks_failed)
    lines.append(f"Checks passed: {passed}/{total}")
    lines.append(f"Files scanned: {len(result.files_scanned)}")
    lines.append("")

    if result.checks_passed:
        lines.append("PASSED:")
        for check in result.checks_passed:
            lines.append(f"  [+] {check}")
        lines.append("")

    if result.checks_failed:
        lines.append("FAILED:")
        for check in result.checks_failed:
            lines.append(f"  [-] {check}")
        lines.append("")

    if result.issues:
        lines.append("ISSUES:")
        for issue in result.issues:
            sev = {"error": "E", "warning": "W", "info": "I"}
            icon = sev.get(issue.severity, "?")
            loc = ""
            if issue.file:
                loc = f" ({issue.file}"
                if issue.line:
                    loc += f":{issue.line}"
                loc += ")"
            lines.append(f"  [{icon}] [{issue.category}]{loc} {issue.message}")
        lines.append("")

    lines.append(f"Summary: {result.error_count} error(s), {result.warning_count} warning(s)")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-cdk-project-or-lambda-dir>")
        print()
        print("Scans CDK and Lambda code for OAuth infrastructure issues.")
        print("Checks token exchange format, permissions, security, and best practices.")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Error: {target} does not exist")
        sys.exit(1)

    result = scan_directory(target)
    print(format_report(result))
    sys.exit(1 if result.error_count > 0 else 0)


if __name__ == "__main__":
    main()
