#!/usr/bin/env python3
"""Scan test files for common anti-patterns and quality issues.

Usage:
    python scan_test_quality.py <path-to-test-files>
    python scan_test_quality.py tests/
    python scan_test_quality.py tests/test_users.py

Checks for:
  - Secret Catcher: test functions with no assert statements
  - Null Assertions: tests that only check `is not None` / `isinstance`
  - Shared Mutable State: global variables modified in test files
  - Test Interdependencies: global keyword usage in test functions
  - Hardcoded Sleeps: time.sleep() calls in test code
  - Enumerated Names: test_1, test_2, etc.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Issue:
    file: str
    line: int
    category: str
    severity: str  # "error", "warning", "info"
    message: str


@dataclass
class ScanResult:
    files_scanned: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


def _make_issue(
    path: str,
    line: int,
    cat: str,
    sev: str,
    msg: str,
) -> Issue:
    """Create an Issue, keeping call sites short."""
    return Issue(path, line, cat, sev, msg)


def scan_file(filepath: Path) -> list[Issue]:
    """Scan a single test file for anti-patterns."""
    issues: list[Issue] = []
    source = filepath.read_text(encoding="utf-8")
    rel = str(filepath)

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append(
            _make_issue(
                rel,
                e.lineno or 0,
                "parse-error",
                "error",
                f"Syntax error: {e.msg}",
            )
        )
        return issues

    _check_module_level_state(tree, rel, issues)
    _check_test_functions(tree, rel, issues)
    return issues


def _check_module_level_state(
    tree: ast.Module,
    rel: str,
    issues: list[Issue],
) -> None:
    """Flag module-level mutable variables (shared state)."""
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.startswith("_"):
                continue
            name = target.id
            if isinstance(node.value, (ast.List, ast.Dict)):
                issues.append(
                    _make_issue(
                        rel,
                        node.lineno,
                        "shared-mutable-state",
                        "error",
                        f"Module-level mutable '{name}' — shared state causes interdependencies",
                    )
                )
            elif isinstance(node.value, ast.Constant) and node.value.value is None:
                issues.append(
                    _make_issue(
                        rel,
                        node.lineno,
                        "shared-mutable-state",
                        "warning",
                        f"Module-level '{name} = None' — may cause interdependency if modified",
                    )
                )


def _check_test_functions(
    tree: ast.Module,
    rel: str,
    issues: list[Issue],
) -> None:
    """Check each test function for anti-patterns."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue

        name = node.name

        # Secret Catcher: no assertions
        has_assert = _has_assertions(node)
        if not has_assert:
            issues.append(
                _make_issue(
                    rel,
                    node.lineno,
                    "secret-catcher",
                    "error",
                    f"'{name}' has no assertions — only passes if no exception is raised",
                )
            )

        # Null Assertions: only vague checks
        if has_assert:
            asserts = _collect_asserts(node)
            if asserts and _all_null_assertions(asserts):
                issues.append(
                    _make_issue(
                        rel,
                        node.lineno,
                        "null-assertions",
                        "warning",
                        f"'{name}' only has vague assertions (is not None, isinstance)",
                    )
                )

        # Global keyword (test interdependency)
        for child in ast.walk(node):
            if isinstance(child, ast.Global):
                issues.append(
                    _make_issue(
                        rel,
                        child.lineno,
                        "test-interdependency",
                        "error",
                        f"'{name}' uses 'global' — don't share state via globals",
                    )
                )

        # Hardcoded sleeps
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            fn = _get_call_name(child)
            if fn in ("time.sleep", "sleep"):
                issues.append(
                    _make_issue(
                        rel,
                        child.lineno,
                        "hardcoded-sleep",
                        "warning",
                        f"'{name}' uses time.sleep() — mock time-dependent operations",
                    )
                )

        # Enumerated names
        if re.match(r"test_\w*_?\d+$", name):
            issues.append(
                _make_issue(
                    rel,
                    node.lineno,
                    "enumerated-name",
                    "warning",
                    f"'{name}' has numeric suffix — use test_[what]_[scenario]_[expected]",
                )
            )


def _has_assertions(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Check if a function contains any assertion."""
    for child in ast.walk(func_node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.Call):
            cn = _get_call_name(child)
            if cn and ("assert" in cn.lower() or cn.endswith(".raises")):
                return True
        if isinstance(child, (ast.With, ast.AsyncWith)):
            for item in child.items:
                if isinstance(item.context_expr, ast.Call):
                    cn = _get_call_name(item.context_expr)
                    if cn and "raises" in cn.lower():
                        return True
    return False


def _collect_asserts(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Assert]:
    """Collect all assert statements in a function."""
    return [child for child in ast.walk(func_node) if isinstance(child, ast.Assert)]


def _all_null_assertions(assert_nodes: list[ast.Assert]) -> bool:
    """Check if all assertions are vague."""
    for node in assert_nodes:
        test = node.test
        # assert x is not None
        if isinstance(test, ast.Compare):
            if (
                len(test.ops) == 1
                and isinstance(test.ops[0], ast.IsNot)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
            ):
                continue
        # assert isinstance(x, Y)
        if isinstance(test, ast.Call):
            cn = _get_call_name(test)
            if cn == "isinstance":
                continue
        # assert len(x) > 0
        if isinstance(test, ast.Compare):
            if isinstance(test.left, ast.Call):
                cn = _get_call_name(test.left)
                if cn == "len":
                    continue
        # This assert is specific enough
        return False
    return True


def _get_call_name(node: ast.Call) -> str | None:
    """Extract the dotted name from a Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = []
        current = func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def scan_path(path: Path) -> ScanResult:
    """Scan a file or directory for test quality issues."""
    result = ScanResult()
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.rglob("test_*.py"))

    for f in files:
        result.files_scanned += 1
        result.issues.extend(scan_file(f))
    return result


def format_report(result: ScanResult) -> str:
    """Format scan results as a readable report."""
    lines: list[str] = []
    lines.append(f"Scanned {result.files_scanned} file(s)")
    lines.append("")

    if not result.issues:
        lines.append("No issues found!")
        return "\n".join(lines)

    by_file: dict[str, list[Issue]] = {}
    for issue in result.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for fpath, file_issues in sorted(by_file.items()):
        lines.append(f"--- {fpath} ---")
        for issue in sorted(file_issues, key=lambda i: i.line):
            sev = {"error": "E", "warning": "W", "info": "I"}
            icon = sev[issue.severity]
            lines.append(f"  [{icon}] L{issue.line}: [{issue.category}] {issue.message}")
        lines.append("")

    lines.append(f"Summary: {result.error_count} error(s), {result.warning_count} warning(s)")
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-test-files>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Error: {target} does not exist")
        sys.exit(1)

    result = scan_path(target)
    print(format_report(result))
    sys.exit(1 if result.error_count > 0 else 0)


if __name__ == "__main__":
    main()
