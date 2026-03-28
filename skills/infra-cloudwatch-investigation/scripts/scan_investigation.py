#!/usr/bin/env python3
"""Scan a CloudWatch investigation transcript for completeness and quality.

Usage:
    python scan_investigation.py <path-to-transcript-or-report>
    python scan_investigation.py investigation-report.md
    python scan_investigation.py transcript.txt

Checks for:
  - Multiple log streams checked (not just one)
  - Noise filtering applied (litellm, ADK warnings)
  - REPORT lines analyzed for Lambda metrics
  - CloudWatch Insights used for complex searches
  - Cross-Lambda correlation attempted (for pipeline issues)
  - Error aggregation performed (not just individual errors)
  - Structured report produced
  - Root cause identified (not just symptoms listed)
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


@dataclass
class ScanResult:
    issues: list[Issue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)

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


def scan_content(content: str) -> ScanResult:
    """Scan investigation content for completeness."""
    result = ScanResult()
    lower = content.lower()

    # Check 1: Multiple log streams
    stream_refs = len(
        re.findall(
            r"describe-log-streams|log.?stream|--max-items\s+[2-9]|\bstream\b.*\bstream\b",
            lower,
        )
    )
    if stream_refs >= 2:
        result.checks_passed.append("multiple-streams")
    else:
        result.checks_failed.append("multiple-streams")
        result.issues.append(
            Issue(
                "incomplete-investigation",
                "warning",
                "Only one log stream appears to have been checked. "
                "Check at least 2-3 recent streams to avoid missing the failure.",
            )
        )

    # Check 2: Noise filtering
    noise_patterns = [
        "loggingworker",
        "logging_worker",
        "litellm",
        "event loop",
        "safe to ignore",
        "noise",
        "filter.*noise",
        "non-blocking",
    ]
    noise_filtered = any(p in lower for p in noise_patterns)
    if noise_filtered:
        result.checks_passed.append("noise-filtering")
    else:
        result.checks_failed.append("noise-filtering")
        result.issues.append(
            Issue(
                "missing-noise-filter",
                "warning",
                "No evidence of noise filtering. litellm LoggingWorker errors "
                "and ADK deprecation warnings should be filtered out to avoid misdiagnosis.",
            )
        )

    # Check 3: REPORT line / Lambda metrics analysis
    metrics_patterns = [
        "report",
        "duration",
        "memory",
        "init duration",
        "billed duration",
        "cold start",
    ]
    metrics_found = sum(1 for p in metrics_patterns if p in lower)
    if metrics_found >= 2:
        result.checks_passed.append("lambda-metrics")
    else:
        result.checks_failed.append("lambda-metrics")
        result.issues.append(
            Issue(
                "missing-metrics",
                "warning",
                "Lambda execution metrics (Duration, Memory, Init Duration) "
                "not analyzed. Check REPORT lines for performance data.",
            )
        )

    # Check 4: CloudWatch Insights usage
    insights_patterns = [
        "start-query",
        "get-query-results",
        "insights",
        "stats count",
        "filter @message",
        "fields @timestamp",
    ]
    insights_used = any(p in lower for p in insights_patterns)
    if insights_used:
        result.checks_passed.append("cloudwatch-insights")
    else:
        result.checks_failed.append("cloudwatch-insights")
        result.issues.append(
            Issue(
                "no-insights",
                "info",
                "CloudWatch Insights was not used. For complex investigations, "
                "Insights queries are faster and more powerful than manual log parsing.",
            )
        )

    # Check 5: Error aggregation
    aggregation_patterns = [
        "count",
        "aggregate",
        "frequency",
        "error rate",
        "stats count",
        "bin(",
        "occurrences",
        "pattern",
    ]
    aggregation_done = sum(1 for p in aggregation_patterns if p in lower) >= 2
    if aggregation_done:
        result.checks_passed.append("error-aggregation")
    else:
        result.checks_failed.append("error-aggregation")
        result.issues.append(
            Issue(
                "no-aggregation",
                "info",
                "No error aggregation found. For intermittent issues, "
                "counting error occurrences over time reveals patterns.",
            )
        )

    # Check 6: Cross-Lambda correlation (only relevant for pipelines)
    pipeline_indicators = [
        "gateway",
        "sub-agent",
        "mcp",
        "pipeline",
        "brainy",
        "brain",
        "agent",
    ]
    is_pipeline = any(p in lower for p in pipeline_indicators)
    if is_pipeline:
        correlation_patterns = [
            "correlat",
            "timestamp",
            "cross-lambda",
            "log-group-names",
            "multiple.*log.*group",
            "t0",
            "trace",
        ]
        correlation_done = any(p in lower for p in correlation_patterns)
        if correlation_done:
            result.checks_passed.append("cross-lambda-correlation")
        else:
            result.checks_failed.append("cross-lambda-correlation")
            result.issues.append(
                Issue(
                    "missing-correlation",
                    "warning",
                    "Pipeline investigation detected but no cross-Lambda correlation. "
                    "Match timestamps across Lambda log groups to trace the request flow.",
                )
            )

    # Check 7: Root cause identified
    root_cause_patterns = [
        "root cause",
        "caused by",
        "the issue is",
        "the problem is",
        "because",
        "due to",
        "found that",
        "identified",
    ]
    root_cause_found = any(p in lower for p in root_cause_patterns)
    if root_cause_found:
        result.checks_passed.append("root-cause-identified")
    else:
        result.checks_failed.append("root-cause-identified")
        result.issues.append(
            Issue(
                "no-root-cause",
                "error",
                "No root cause identified. An investigation should conclude with "
                "a clear explanation of what went wrong and why.",
            )
        )

    # Check 8: Recommendation provided
    recommendation_patterns = [
        "recommend",
        "fix",
        "remediat",
        "action",
        "next step",
        "should",
        "resolution",
    ]
    recommendation_found = sum(1 for p in recommendation_patterns if p in lower) >= 2
    if recommendation_found:
        result.checks_passed.append("recommendation")
    else:
        result.checks_failed.append("recommendation")
        result.issues.append(
            Issue(
                "no-recommendation",
                "error",
                "No recommendation provided. An investigation should end with "
                "clear next steps for fixing the issue.",
            )
        )

    # Check 9: AWS profile / region specified
    env_patterns = [
        "aws_profile",
        "aws profile",
        "--profile",
        "--region",
        "us-east-1",
        "us-west-2",
    ]
    env_specified = any(p in lower for p in env_patterns)
    if env_specified:
        result.checks_passed.append("environment-specified")
    else:
        result.checks_failed.append("environment-specified")
        result.issues.append(
            Issue(
                "missing-environment",
                "warning",
                "AWS profile and region not specified. Always document which "
                "environment was investigated.",
            )
        )

    return result


def format_report(result: ScanResult) -> str:
    """Format scan results as a readable report."""
    lines: list[str] = []
    lines.append(f"Investigation Completeness Score: {result.score:.0f}%")
    passed = len(result.checks_passed)
    total = passed + len(result.checks_failed)
    lines.append(f"Checks passed: {passed}/{total}")
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
            icon = sev[issue.severity]
            lines.append(f"  [{icon}] [{issue.category}] {issue.message}")
        lines.append("")

    lines.append(f"Summary: {result.error_count} error(s), {result.warning_count} warning(s)")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-transcript-or-report>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Error: {target} does not exist")
        sys.exit(1)

    content = target.read_text(encoding="utf-8")
    result = scan_content(content)
    print(format_report(result))
    sys.exit(1 if result.error_count > 0 else 0)


if __name__ == "__main__":
    main()
