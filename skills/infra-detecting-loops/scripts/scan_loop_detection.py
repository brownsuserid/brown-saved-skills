#!/usr/bin/env python3
"""Scan a loop detection audit transcript or report for completeness and quality.

Usage:
    python scan_loop_detection.py <path-to-transcript-or-report>
    python scan_loop_detection.py loop-detection-report.md
    python scan_loop_detection.py transcript.txt

Checks for:
  - Project structure mapped (EventBridge, Lambda, SFN, DynamoDB streams)
  - Trigger chains traced end-to-end
  - Failure paths analyzed (not just happy path)
  - Step Function cycle detection performed
  - Defense mechanisms audited (concurrency, DLQ, timeout, idempotency)
  - cfn-lint / Checkov scans run
  - Severity classification used
  - Blast radius assessed
  - Specific remediation provided (not generic advice)
  - Structured report produced
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
    """Scan loop detection output for completeness."""
    result = ScanResult()
    lower = content.lower()

    # Check 1: Project structure mapped
    structure_patterns = [
        "eventbridge",
        "event bridge",
        "lambda",
        "step function",
        "state machine",
        "dynamodb",
        "sqs",
        "sns",
        "s3.*notification",
        "trigger",
        "event source",
    ]
    structure_found = sum(1 for p in structure_patterns if re.search(p, lower))
    if structure_found >= 3:
        result.checks_passed.append("project-structure-mapped")
    else:
        result.checks_failed.append("project-structure-mapped")
        result.issues.append(
            Issue(
                "incomplete-mapping",
                "error",
                "Project structure not fully mapped. A loop audit must identify "
                "all event-driven components: EventBridge rules, Lambdas, Step Functions, "
                "DynamoDB streams, SQS queues, and SNS topics.",
            )
        )

    # Check 2: Trigger chains traced
    chain_patterns = [
        r"->",
        r"→",
        "trigger.*chain",
        "event.*flow",
        "invokes?",
        "fires?",
        "triggers?.*lambda",
        "chain",
    ]
    chain_found = sum(1 for p in chain_patterns if re.search(p, lower))
    if chain_found >= 2:
        result.checks_passed.append("trigger-chains-traced")
    else:
        result.checks_failed.append("trigger-chains-traced")
        result.issues.append(
            Issue(
                "missing-chain-analysis",
                "error",
                "Trigger chains not traced. Every event source must be traced "
                "to its Lambda target and through to its side effects to detect loops.",
            )
        )

    # Check 3: Failure paths analyzed
    failure_patterns = [
        "failure",
        "error path",
        "error handling",
        "on failure",
        "except",
        "catch",
        "fails?",
        "retry",
        "error case",
    ]
    failure_found = sum(1 for p in failure_patterns if re.search(p, lower))
    if failure_found >= 2:
        result.checks_passed.append("failure-paths-analyzed")
    else:
        result.checks_failed.append("failure-paths-analyzed")
        result.issues.append(
            Issue(
                "missing-failure-analysis",
                "error",
                "Failure paths not analyzed. Most loops manifest during error handling, "
                "not happy paths. Check what happens when Lambda processing fails — "
                "is the trigger condition still cleared?",
            )
        )

    # Check 4: Defense mechanisms audited
    defense_patterns = [
        "concurrency",
        "reserved.concurrent",
        "dead.letter",
        "dlq",
        "timeout",
        "idempoten",
        "circuit.breaker",
        "max.retries",
        "max.attempts",
        "dedup",
    ]
    defenses_found = sum(1 for p in defense_patterns if re.search(p, lower))
    if defenses_found >= 3:
        result.checks_passed.append("defense-mechanisms-audited")
    else:
        result.checks_failed.append("defense-mechanisms-audited")
        result.issues.append(
            Issue(
                "missing-defense-audit",
                "warning",
                "Defense mechanisms not fully audited. Check for: concurrency limits, "
                "DLQ configuration, timeout settings, idempotency handling, "
                "and circuit breaker patterns.",
            )
        )

    # Check 5: Severity classification used
    severity_patterns = [
        "critical",
        "high",
        "medium",
        "low",
        "severity",
        "risk level",
        "priority",
    ]
    severity_found = sum(1 for p in severity_patterns if re.search(p, lower))
    if severity_found >= 2:
        result.checks_passed.append("severity-classification")
    else:
        result.checks_failed.append("severity-classification")
        result.issues.append(
            Issue(
                "missing-severity",
                "warning",
                "Findings not classified by severity. Use CRITICAL/HIGH/MEDIUM/LOW "
                "to help prioritize remediation effort.",
            )
        )

    # Check 6: Blast radius assessed
    blast_patterns = [
        "blast radius",
        "cost impact",
        "cost per",
        "data corruption",
        "downstream",
        "impact",
        "consequence",
        r"\$\d+",
        "per hour",
        "per minute",
    ]
    blast_found = sum(1 for p in blast_patterns if re.search(p, lower))
    if blast_found >= 2:
        result.checks_passed.append("blast-radius-assessed")
    else:
        result.checks_failed.append("blast-radius-assessed")
        result.issues.append(
            Issue(
                "missing-blast-radius",
                "warning",
                "Blast radius not assessed. For each loop risk, estimate the impact: "
                "cost (Lambda invocations, data transfer), data integrity "
                "(duplicates, corruption), and downstream effects.",
            )
        )

    # Check 7: Specific remediation provided
    remediation_patterns = [
        "recommend",
        "fix",
        "remediat",
        "three.state",
        "flag.*pattern",
        "prefix.*filter",
        "separate.*bucket",
        "maxattempts",
        "maxconcurrency",
        "code change",
        "add.*catch",
    ]
    remediation_found = sum(1 for p in remediation_patterns if re.search(p, lower))
    if remediation_found >= 3:
        result.checks_passed.append("specific-remediation")
    else:
        result.checks_failed.append("specific-remediation")
        result.issues.append(
            Issue(
                "generic-remediation",
                "error",
                "Remediation is too generic. Provide specific code changes, "
                "CDK configuration updates, or ASL modifications — not just "
                "'add error handling' or 'set a timeout'.",
            )
        )

    # Check 8: cfn-lint or Checkov run (only if CDK project)
    cdk_indicators = ["cdk", "cloudformation", "stack", "synthesize", "synth"]
    is_cdk = any(p in lower for p in cdk_indicators)
    if is_cdk:
        scan_patterns = [
            "cfn-lint",
            "cfn.lint",
            "checkov",
            "cdk-nag",
            "cdk.nag",
            "e3004",
            "circular dependency",
        ]
        scan_run = any(re.search(p, lower) for p in scan_patterns)
        if scan_run:
            result.checks_passed.append("infrastructure-scans")
        else:
            result.checks_failed.append("infrastructure-scans")
            result.issues.append(
                Issue(
                    "missing-infra-scans",
                    "info",
                    "CDK project detected but cfn-lint/Checkov not run. "
                    "These tools catch CloudFormation circular dependencies (E3004) "
                    "that waste deployment time.",
                )
            )

    # Check 9: Step Function analysis (only if SFN present)
    sfn_indicators = [
        "step function",
        "state machine",
        "sfn",
        "asl",
        r"\.asl\.json",
    ]
    has_sfn = any(re.search(p, lower) for p in sfn_indicators)
    if has_sfn:
        sfn_patterns = [
            "choice.*state",
            "cycle",
            "back.*edge",
            "loop.*back",
            "retry.*config",
            "maxattempts",
            "timeout.*seconds",
            "map.*state",
            "unbounded",
        ]
        sfn_analyzed = sum(1 for p in sfn_patterns if re.search(p, lower))
        if sfn_analyzed >= 2:
            result.checks_passed.append("step-function-analysis")
        else:
            result.checks_failed.append("step-function-analysis")
            result.issues.append(
                Issue(
                    "incomplete-sfn-analysis",
                    "warning",
                    "Step Functions detected but not fully analyzed. Check for: "
                    "Choice state cycles, unbounded retry configs, Map state "
                    "output explosions, and missing execution timeouts.",
                )
            )

    # Check 10: Structured report produced
    report_patterns = [
        "executive summary",
        "finding[s]?",
        "remediation plan",
        "architecture overview",
        "defense.*audit",
        "## ",
        "### ",
    ]
    report_found = sum(1 for p in report_patterns if re.search(p, lower))
    if report_found >= 3:
        result.checks_passed.append("structured-report")
    else:
        result.checks_failed.append("structured-report")
        result.issues.append(
            Issue(
                "no-structured-report",
                "warning",
                "No structured report produced. Use the loop detection report template "
                "to organize findings with executive summary, architecture overview, "
                "findings, defense audit, and remediation plan.",
            )
        )

    return result


def format_report(result: ScanResult) -> str:
    """Format scan results as a readable report."""
    lines: list[str] = []
    lines.append(f"Loop Detection Audit Completeness Score: {result.score:.0f}%")
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
