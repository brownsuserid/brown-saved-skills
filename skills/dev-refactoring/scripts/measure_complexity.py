#!/usr/bin/env python3
"""Measure code complexity before and after refactoring.

Usage:
    # Measure a single file
    python scripts/measure_complexity.py path/to/file.py

    # Compare before/after (pass two files or same file at different git refs)
    python scripts/measure_complexity.py path/to/file.py --before HEAD~1

    # Measure a directory
    python scripts/measure_complexity.py src/

Output: JSON with per-function complexity, averages, and pass/fail against thresholds.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_radon(path: str) -> list[dict]:
    """Run radon cc on a path and return parsed results."""
    try:
        result = subprocess.run(
            ["uv", "run", "radon", "cc", path, "-s", "-j"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Try without uv
            result = subprocess.run(
                ["radon", "cc", path, "-s", "-j"],
                capture_output=True,
                text=True,
            )
        data = json.loads(result.stdout) if result.stdout else {}
    except (FileNotFoundError, json.JSONDecodeError):
        print("Error: radon not found. Install with: uv add --dev radon", file=sys.stderr)
        sys.exit(1)

    functions = []
    for filepath, items in data.items():
        for item in items:
            functions.append(
                {
                    "file": filepath,
                    "name": item.get("name", "unknown"),
                    "type": item.get("type", "unknown"),
                    "complexity": item.get("complexity", 0),
                    "rank": item.get("rank", "?"),
                    "lineno": item.get("lineno", 0),
                    "endline": item.get("endline", 0),
                    "length": item.get("endline", 0) - item.get("lineno", 0) + 1,
                }
            )
    return functions


def analyze(functions: list[dict]) -> dict:
    """Produce summary statistics from function complexity data."""
    if not functions:
        return {
            "functions": [],
            "summary": {"count": 0, "avg_complexity": 0, "max_complexity": 0, "over_10": 0},
        }

    complexities = [f["complexity"] for f in functions]
    over_10 = [f for f in functions if f["complexity"] > 10]

    return {
        "functions": sorted(functions, key=lambda f: -f["complexity"]),
        "summary": {
            "count": len(functions),
            "avg_complexity": round(sum(complexities) / len(complexities), 2),
            "max_complexity": max(complexities),
            "over_10": len(over_10),
            "over_10_names": [f"{f['file']}:{f['name']} ({f['complexity']})" for f in over_10],
        },
    }


def get_file_at_ref(filepath: str, ref: str) -> str | None:
    """Get file content at a git ref, write to temp file, return path."""
    import tempfile

    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{filepath}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        tmp.write(result.stdout)
        tmp.close()
        return tmp.name
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Measure code complexity")
    parser.add_argument("path", help="File or directory to analyze")
    parser.add_argument("--before", help="Git ref to compare against (e.g., HEAD~1, main)")
    parser.add_argument(
        "--threshold", type=int, default=10, help="Max acceptable complexity (default: 10)"
    )
    args = parser.parse_args()

    # Current analysis
    current = analyze(run_radon(args.path))

    output = {"current": current}

    # Comparison if requested
    if args.before:
        path = Path(args.path)
        if path.is_file():
            before_path = get_file_at_ref(args.path, args.before)
            if before_path:
                before = analyze(run_radon(before_path))
                Path(before_path).unlink()
                output["before"] = before
                output["delta"] = {
                    "avg_complexity": round(
                        current["summary"]["avg_complexity"] - before["summary"]["avg_complexity"],
                        2,
                    ),
                    "max_complexity": current["summary"]["max_complexity"]
                    - before["summary"]["max_complexity"],
                    "over_10": current["summary"]["over_10"] - before["summary"]["over_10"],
                }

    # Pass/fail
    output["threshold"] = args.threshold
    output["pass"] = current["summary"]["max_complexity"] <= args.threshold

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
