---
name: refactoring
description: Improves code structure and quality when code becomes difficult to maintain, has duplication, or shows signs of technical debt. Uses incremental refactoring strategies to prevent AI-generated code bloat while preserving functionality and keeping tests passing.
---

# Refactoring Skill

Refactoring means improving code structure without changing external behavior. The hard part isn't knowing *what* to change — it's doing it safely, incrementally, and verifiably. This skill focuses on that discipline.

## The Golden Rule: Characterization Tests First

Before touching any code, you need a safety net. This is non-negotiable, and here's why: without tests that capture current behavior, you can't tell whether your refactoring broke something or simply changed it. The tests are your proof that the refactoring preserved behavior.

**Your first action on any refactoring task:**

1. Read the code you're about to refactor
2. Check what tests exist: `pytest tests/ -v --co -q` (collect only, no run)
3. Check coverage: `pytest --cov=<module> --cov-report=term-missing tests/`
4. If coverage is below 80%, write characterization tests *before changing anything*
5. Run the tests, confirm they pass: `pytest tests/ -v`
6. Commit the tests: `git commit -m "test: add characterization tests for <module>"`

Characterization tests capture *what the code does now*, not what it should do. They're not aspirational — they're documentary. Test the public API, edge cases, error paths, and any behavior you can observe. This commit is your safety net and your rollback point.

For comprehensive test-writing guidance, see [../dev-writing-unit-tests/SKILL.md](../dev-writing-unit-tests/SKILL.md).

---

## The Refactoring Loop

After your characterization tests are committed, refactoring follows a tight loop. Each iteration should be small enough that if the tests break, you know exactly what caused it.

```
Extract/simplify ONE thing → Run tests → Commit → Repeat
```

**Concretely, your first refactoring move should be:**

1. Pick the highest-complexity function (use `measure_complexity.py` — see below)
2. Identify one extractable responsibility (validation, calculation, I/O, formatting)
3. Extract it into a new method/function
4. Run tests — they must still pass
5. Commit: `git commit -m "refactor: extract <name> from <source>"`
6. Measure complexity again to confirm improvement
7. Pick the next extraction and repeat

This loop continues until the code meets quality thresholds (see "Quality Metrics" below).

**Why this matters:** Large-scale rewrites are tempting but dangerous. They make it impossible to isolate which change broke something. Small extractions are individually verifiable and easy to revert.

---

## Phase 1: Identify What to Refactor

### Measure Complexity

```bash
uv add --dev radon
python scripts/measure_complexity.py src/
```

This bundled script runs `radon cc` and outputs JSON with per-function complexity, averages, and pass/fail against the threshold. Functions with cyclomatic complexity > 10 are your primary targets.

**You can also compare before/after:**
```bash
python scripts/measure_complexity.py src/module.py --before HEAD~3
```

### Find Duplication

```bash
uv add --dev pylint
uv run pylint --disable=all --enable=duplicate-code .
```

### Find Dead Code

```bash
uv add --dev vulture
uv run vulture .
```

### Prioritize by Change Frequency

```bash
git log --format=format: --name-only | grep -v '^$' | grep '\.py$' | sort | uniq -c | sort -rn | head -20
```

**High change frequency + high complexity = top priority.** These are the files that cause the most pain and will benefit most from refactoring.

### Run Anti-Pattern Scan

For a comprehensive automated audit, see [../dev-reviewing-code/SKILL.md](../dev-reviewing-code/SKILL.md) (use Deep Scan mode for anti-pattern detection).

### Manual Code Smell Review

Look for:
- Long functions (high cyclomatic complexity)
- Deep nesting (nested if/else chains)
- Duplicate code blocks
- God objects (classes doing too much — many unrelated methods)
- Feature envy (method uses another class's data more than its own)
- Magic numbers (unexplained constants)
- Error swallowing (`except Exception` returning defaults)

**Complete code smell catalog:** See `references/refactoring-patterns.md`

---

## Phase 2: Refactor Incrementally

Use the TodoWrite tool to track each extraction step.

### Common Techniques

**Extract Method** — The most common refactoring. Pull a block of logic into its own method:
```python
# Before: 150-line process_order with inline validation, pricing, shipping
def process_order(order):
    # validation logic...
    # pricing logic...
    # shipping logic...

# After: High-level workflow that reads like a summary
def process_order(order):
    validate_order(order)
    totals = calculate_totals(order)
    return process_payment(order, totals)
```

**Simplify Conditionals** — Replace nested if/else with early returns:
```python
# Before
if user:
    if user.is_authenticated:
        if resource:
            if resource.is_public or user.is_admin:
                return True
return False

# After
if not user or not user.is_authenticated:
    return False
if not resource:
    return False
return resource.is_public or user.is_admin
```

**Replace Magic Numbers:**
```python
# Before
if weight > 50:
    return weight * 0.05

# After
HEAVY_PACKAGE_THRESHOLD_LBS = 50
HEAVY_PACKAGE_RATE = 0.05
if weight > HEAVY_PACKAGE_THRESHOLD_LBS:
    return weight * HEAVY_PACKAGE_RATE
```

**Consolidate AI-Generated Duplication** — AI tools often generate near-identical functions with minor variations. Consolidate into parameterized versions:
```python
# Before: AI generated three nearly identical functions
def get_active_users(): ...
def get_inactive_users(): ...
def get_pending_users(): ...

# After: Single parameterized function
def get_users_by_status(status: str) -> list[User]:
    valid_statuses = {"active", "inactive", "pending"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}")
    return User.query.filter_by(status=status).all()
```

To find AI duplication patterns:
```bash
rg "^def (get_|calculate_|process_)" --type py | sort
```

**Complete refactoring catalog:** See `references/refactoring-patterns.md`

### Architecture-Level Refactoring

For multi-file or infrastructure refactoring (e.g., serverless event loops, circular dependencies):

1. **Map the architecture first** — Create a Mermaid diagram of component relationships
2. **Identify the structural problem** — Circular dependencies, missing abstractions, tangled event chains
3. **Plan the target architecture** — Draw the "after" diagram
4. **Refactor in layers** — Start from the innermost dependency and work outward
5. **Add integration tests** that verify the structural fix (e.g., "event A does not re-trigger handler B")

**Standards:** See `../dev-shared-references/architecture-diagrams.md`

---

## Phase 3: Verify Quality

After each refactoring cycle, verify the improvement.

### Quality Metrics

Use these metrics to judge refactoring quality. They're based on industry best practices (cyclomatic complexity thresholds from Carnegie Mellon SEI research):

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Cyclomatic complexity per function | ≤ 10 | `python scripts/measure_complexity.py src/` |
| Average complexity reduced | Lower than before | `python scripts/measure_complexity.py src/module.py --before <ref>` |
| Test coverage | ≥ 90% | `pytest --cov=<module> --cov-report=term-missing` |
| Duplication | < 5% | `pylint --disable=all --enable=duplicate-code` |
| All tests passing | 100% | `pytest tests/ -v` |

**Why cyclomatic complexity, not line count?** Line count is misleading — good refactoring often *adds* lines (type hints, docstrings, better variable names) while reducing complexity. A 60-line orchestrator method with complexity 3 (simple sequential calls) is better than a 30-line method with complexity 15 (deeply nested branches). Complexity measures how hard code is to understand and test, which is what actually matters.

### Run Quality Checks

```bash
# Tests
pytest tests/ -v

# Complexity
python scripts/measure_complexity.py src/

# Type checking
mypy src/

# Linting + formatting
ruff check --fix src/
ruff format src/

# Security
bandit -c pyproject.toml -r src/
```

### Before/After Comparison

After completing refactoring, summarize the improvement:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Max complexity | 23 | 8 | -65% |
| Avg complexity | 12.4 | 4.2 | -66% |
| Functions > 10 | 3 | 0 | Eliminated |
| Test coverage | 42% | 95% | +53pp |
| Tests | 3 | 45 | +42 |

---

## Phase 4: Document and Commit

### Commit Format

```bash
git commit -m "$(cat <<'EOF'
refactor: consolidate user queries

Refactored user queries to eliminate duplication:
- Consolidated 3 functions into 1 parameterized function
- Max complexity reduced from 23 to 8
- All tests passing, coverage 42% → 95%

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Complete git/PR workflow:** See [../dev-shared-references/git-and-pr-workflow.md](../dev-shared-references/git-and-pr-workflow.md)

---

## Key Principles

- **Tests first, always.** Write characterization tests before any change. Commit them separately.
- **One extraction at a time.** Extract → Test → Commit → Repeat. Never batch multiple refactoring steps into one untested change.
- **Measure, don't guess.** Use `measure_complexity.py` to verify improvement with numbers.
- **Complexity over line count.** A long, simple orchestrator is fine. A short, tangled function is not.
- **Keep refactoring separate from features.** Refactoring PRs should only refactor.
- **Consolidate AI duplication immediately.** Don't let near-identical generated functions accumulate.
- **Preserve external behavior.** Same inputs must produce same outputs. Tests prove this.

## When to Use This Skill

- Code is difficult to maintain or understand
- Duplication discovered across functions or files
- Before adding features to complex code
- After AI generates repetitive code patterns
- Code review identifies structural issues
- High-complexity functions flagged by tooling
- Circular dependencies or tangled event chains in architecture

## Common Mistakes

- Refactoring without tests (no safety net to catch breakage)
- Big-bang rewrites instead of incremental extractions
- Mixing refactoring with feature work in the same PR
- Measuring success by line count instead of complexity
- Skipping the commit after each successful extraction
- Not running tests between each change
