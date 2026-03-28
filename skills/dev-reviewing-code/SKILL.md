---
name: reviewing-code
description: Performs comprehensive code review and anti-pattern detection. Use for PR reviews, branch comparisons, or whole-project scans. TRIGGER when the user mentions: code review, review PR, review this code, check for anti-patterns, scan for code smells, technical debt audit, find anti-patterns, code quality audit, or "what's wrong with this code". Covers PR review with prioritized feedback, project-wide anti-pattern scanning across Python/React/AWS/testing, error-swallowing detection, and architecture review. Do NOT use for implementing fixes (use dev-refactoring), writing tests (use dev-writing-unit-tests), or CDK-specific quality checks (use infra-cdk-quality).
---

# Code Review & Anti-Pattern Detection Skill

This skill operates in two modes:

- **PR/Change Review** — Review a PR, branch diff, or specific files with prioritized feedback
- **Deep Scan** — Scan an entire project for anti-patterns, code smells, and technical debt

Both modes use the same priority categories and comment format. Choose the mode based on scope.

## Process Overview

Use the TodoWrite tool to track progress through applicable phases:

---

## Mode Selection

**PR/Change Review** (Phases 1-4): User provides a PR number, branch, or files to review.

**Deep Scan** (Phases 5-8): User asks for a project-wide audit, anti-pattern scan, or technical debt assessment.

If you spot systemic issues during a PR review, recommend switching to Deep Scan mode for a comprehensive assessment.

---

## PR/CHANGE REVIEW (Phases 1-4)

### Phase 1: Gather Changes

Adapt to whatever the user gives you:

**PR number:** Use `gh pr view [N]`, `gh pr diff [N]`, and `gh pr checks [N]` to get the full picture.

**Branch comparison:** Use `git diff main...HEAD` and `git log main..HEAD --oneline` to understand scope.

**Specific files:** Read them directly.

For PRs, always check CI status with `gh pr checks`. If automated checks are failing, flag that immediately — there's no point doing a detailed review of code that doesn't pass tests or linting. Comment with `gh pr comment [N] --body "..."` listing the failures and ask the author to fix before re-requesting review.

### Phase 2: Review Focus

Claude is already good at spotting common issues. This skill exists to enforce things that are easy to overlook or that require project context.

#### Project-Specific Standards

These are the standards for this project. Flag violations:

- **Type hints required** on all function parameters and return types
- **Google-style docstrings** on all public functions and classes
- **Integration tests** must be tagged with `@pytest.mark.integration`
- **Test coverage target:** 90%+ for new code
- **Conventional commit messages** (e.g., `feat:`, `fix:`, `refactor:`)
- **Import organization:** stdlib → third-party → local
- **Error handling:** Use specific exceptions. Broad `except Exception` that returns defaults without re-raising is an anti-pattern — it hides real errors. The only acceptable use of broad exception handlers is at API boundaries where you must return a response, and even there the exception should be logged with `exc_info=True`.

#### Error-Swallowing Detection

This is a critical pattern that gets past most reviewers. Actively scan for:

```python
# BAD — silently hides failures
try:
    result = do_something()
except Exception:
    return {}  # Caller never knows it failed

# BAD — logs but still swallows
try:
    config = parse_config(path)
except Exception as e:
    logger.warning(f"Parse failed: {e}")
    return default_config  # Real error is lost

# GOOD — specific exception, appropriate handling
try:
    user = get_user(user_id)
except UserNotFoundError:
    logger.warning(f"User {user_id} not found")
    return None
# Other exceptions propagate — they indicate real problems
```

#### Scope Check

If the diff exceeds ~500 lines changed or touches many unrelated concerns, flag it and recommend splitting into focused PRs. Large PRs get worse reviews and are harder to revert.

#### Architecture Fit

When the change modifies system structure (new services, changed data flow, new dependencies), check:
- Does it fit existing patterns or does it introduce a new one without justification?
- Are architecture diagrams updated if structure changed? (see `../dev-shared-references/architecture-diagrams.md`)
- Is coupling appropriate?

### Phase 3: Deliver Feedback

#### Priority Categories

Organize findings into these tiers:

- **Critical (must fix):** Security vulnerabilities, data loss risks, runtime crashes
- **Important (should fix):** Logic errors, missing tests for new code, standards violations, error swallowing
- **Suggestions (optional):** Refactoring opportunities, performance improvements, naming
- **Positive:** Call out good work — thorough tests, clean error handling, clever solutions

#### Comment Format

For each issue, be specific:

```
[Priority] **[Type]: [Brief description]**
File: `path/to/file.py:42`

❌ Current: [show the problematic code]
✅ Fix: [show the concrete fix]
Why: [explain the impact]
```

Don't just observe problems — suggest fixes. Don't nitpick formatting or style that ruff/black handles automatically.

### Phase 4: Post the Review

For PRs, post the review using `gh pr review`:

```bash
# If issues found
gh pr review [N] --request-changes --body "$(cat review.md)"

# If approved
gh pr review [N] --approve --body "LGTM! [brief positive summary]"
```

Decision criteria:
- **Approve** if no critical/important issues remain and automated checks pass
- **Request changes** if critical issues exist or important issues need addressing
- **Reject** if the approach is fundamentally wrong or the PR is too large to review effectively

---

## DEEP SCAN — PROJECT-WIDE ANTI-PATTERN DETECTION (Phases 5-8)

### Phase 5: Project Assessment

Determine project scope and technologies used.

#### Identify Technologies

```bash
# Check for Python
ls pyproject.toml setup.py requirements.txt 2>/dev/null

# Check for React/JavaScript
ls package.json 2>/dev/null

# Check for AWS CDK/CloudFormation
ls cdk.json **/cdk.json **/*.template.json **/*.yaml 2>/dev/null

# Check for Terraform
ls *.tf **/*.tf 2>/dev/null
```

#### Create Detection Plan

Based on findings, select applicable detection phases:
- **Python projects:** Phase 6 General + Python-specific checks
- **React projects:** Phase 6 General + React-specific checks
- **AWS projects:** Phase 6 General + AWS-specific checks
- **All projects:** Testing anti-patterns, Architecture anti-patterns

### Phase 6: Code Anti-Pattern Detection

#### General Code Smells (All Languages)

```bash
# Find large files (potential God Classes)
find . -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" | \
  xargs wc -l 2>/dev/null | sort -rn | head -20

# Find deeply nested directories (complexity indicator)
find . -type d -mindepth 5 | head -10

# Detect TODO/FIXME/HACK comments
rg -i "TODO|FIXME|HACK|XXX" --type-add 'code:*.{py,ts,tsx,js,jsx}' -t code
```

**Code Smells Checklist:**
- [ ] God Classes (>500 lines, multiple responsibilities)
- [ ] Long Methods (>50 lines)
- [ ] Deep Nesting (>4 levels)
- [ ] Magic Numbers (unexplained constants)
- [ ] Dead Code (unused functions/imports)
- [ ] Copy-Paste Code (duplication)
- [ ] Feature Envy (method uses another class's data excessively)
- [ ] Inappropriate Intimacy (classes too dependent)
- [ ] Message Chains (a.b.c.d.method())
- [ ] Global Variables (shared mutable state)

**Complete catalog:** See `references/general-antipatterns.md`

#### Python-Specific Anti-Patterns

```bash
# Complexity analysis
uv run radon cc . -s -a --total-average

# Dead code detection
uv run vulture .

# Duplicate code
uv run pylint --disable=all --enable=duplicate-code .

# Anti-pattern detection with wemake
uv run flake8 --select=WPS . 2>/dev/null || echo "Install wemake-python-styleguide for WPS checks"
```

**Python Checklist:**
- [ ] Mutable default arguments (`def foo(items=[])`)
- [ ] Wildcard imports (`from module import *`)
- [ ] Bare except clauses (`except:`)
- [ ] Error swallowing — `except Exception` returning defaults without re-raising
- [ ] Log-and-forget — catching exceptions, logging them, then continuing
- [ ] Using `type()` instead of `isinstance()`
- [ ] Not using context managers for files
- [ ] Returning multiple types from functions
- [ ] Using `==` for None/True/False comparisons
- [ ] String concatenation in loops

**Error Swallowing Detection (Automated):**

```bash
# Find except Exception blocks that return without re-raising
rg -U "except Exception.*:\n\s+.*\n\s+return" --type py

# Find except blocks with pass/continue (silent swallowing)
rg -U "except.*:\n\s+(pass|continue)" --type py

# Find broad except blocks — review each for proper re-raise
rg "except Exception" --type py -n

# Find except blocks that return default values
rg -U "except.*:\n.*return (\[\]|\{\}|None|\"\")" --type py
```

**Complete Python anti-patterns:** See `references/python-antipatterns.md`

#### React Anti-Patterns

```bash
# Find large components
find . -name "*.tsx" -o -name "*.jsx" | xargs wc -l 2>/dev/null | sort -rn | head -20

# Detect inline object/array props
rg "={(\{|\[)" --type ts --type tsx -g "*.tsx" -g "*.jsx"

# Find index as key anti-pattern
rg "key=\{.*index" --type ts -g "*.tsx" -g "*.jsx"

# Detect potential prop drilling (many props)
rg "props\." --type ts -g "*.tsx" -g "*.jsx" -c | sort -t: -k2 -rn | head -10
```

**React Checklist:**
- [ ] Storing derived state instead of computing
- [ ] Direct state mutation
- [ ] Missing hook dependencies
- [ ] Props drilling (passing through many layers)
- [ ] Using array index as key
- [ ] Inline object/array props causing re-renders
- [ ] Components doing too much (500+ lines)
- [ ] useEffect for synchronous computations
- [ ] Missing memoization where needed
- [ ] Rendering entire lists without virtualization

**Complete React anti-patterns:** See `references/react-antipatterns.md`

#### AWS Infrastructure Anti-Patterns

```bash
# Run cdk-nag if available
cd [CDK_PROJECT] && cdk synth 2>&1 | grep -i "warning\|error"

# Check for hardcoded values
rg "(arn:aws|amazonaws\.com|[0-9]{12})" --type ts -g "*.ts"

# Find public resources
rg -i "public.*true|publicly.*accessible" --type ts --type yaml
```

**AWS Checklist:**
- [ ] Lift-and-shift without cloud optimization
- [ ] Hardcoded ARNs/account IDs
- [ ] Overly permissive IAM policies
- [ ] Public S3 buckets / unencrypted data at rest
- [ ] Missing VPC endpoints for AWS services
- [ ] Security groups with 0.0.0.0/0
- [ ] No observability (CloudWatch, X-Ray)
- [ ] Missing cost allocation tags
- [ ] No backup/retention policies

**Complete AWS anti-patterns:** See `references/aws-antipatterns.md`

#### Testing Anti-Patterns

```bash
# Find tests without assertions
rg "def test_" -A 20 tests/ | rg -v "assert|pytest.raises|expect"

# Check test isolation (shared state)
rg "^[a-zA-Z_]+ = " tests/ --type py

# Find commented-out tests
rg "# *def test_|# *it\(" tests/
```

**Testing Checklist:**
- [ ] Tests without assertions (Secret Catcher)
- [ ] Test interdependencies (order-dependent)
- [ ] Excessive mocking (testing mocks, not code)
- [ ] Flaky tests (non-deterministic)
- [ ] Slow tests not marked as integration
- [ ] Missing edge case coverage
- [ ] Copy-paste test code
- [ ] Testing implementation, not behavior

**Complete testing anti-patterns:** See `references/testing-antipatterns.md`

### Phase 7: Architecture Anti-Patterns

```bash
# Find circular imports (Python)
uv run pydeps . --show-cycles 2>/dev/null || echo "Install pydeps for cycle detection"

# Analyze module dependencies
rg "^from |^import " --type py | cut -d: -f2 | sort | uniq -c | sort -rn | head -20

# Find God modules (high import count)
rg "from [a-z_]+ import" --type py -o | cut -d' ' -f2 | sort | uniq -c | sort -rn | head -10
```

**Generate dependency graphs** using Mermaid flowcharts to make anti-patterns visible. Use subgraphs for architectural layers to expose tight coupling.

**Architecture Checklist:**
- [ ] Circular dependencies
- [ ] God modules (everything imports from one place)
- [ ] Tight coupling between layers
- [ ] Missing abstraction layers
- [ ] Spaghetti architecture
- [ ] Golden Hammer (same pattern everywhere)
- [ ] Boat Anchor (unused kept "just in case")

### Phase 8: Generate Report

Compile findings into prioritized report using template: `templates/antipattern-report.md`

| Priority | Criteria | Action |
|----------|----------|--------|
| Critical | Security vulnerabilities, data loss risk | Fix immediately |
| High | Bugs, major performance issues | Fix this sprint |
| Medium | Maintainability, code smells | Plan remediation |
| Low | Style, minor improvements | Address opportunistically |

For each anti-pattern found:
1. Document location (file:line)
2. Explain the issue
3. Suggest specific fix
4. Estimate effort (S/M/L)
5. Link to reference material

---

## Supporting Files Reference

### Code Review
- `../dev-shared-references/coding-standards.md` — Full Python coding standards
- `../dev-shared-references/architecture-diagrams.md` — Mermaid diagram standards

### Anti-Pattern Catalogs
- `references/general-antipatterns.md` — Language-agnostic code smells
- `references/python-antipatterns.md` — Python-specific issues
- `references/react-antipatterns.md` — React component issues
- `references/aws-antipatterns.md` — AWS infrastructure issues
- `references/testing-antipatterns.md` — Testing code smells

### Output Templates
- `templates/antipattern-report.md` — Structured findings report
- `templates/pr-review-template.md` — PR review output template

---

## Key Principles

- **Systematic detection:** Use automated tools first, then manual review
- **Prioritize findings:** Critical security > bugs > maintainability
- **Context matters:** Some "anti-patterns" are acceptable trade-offs
- **Actionable output:** Every finding includes a concrete fix
- **Don't nitpick:** Skip formatting/style that ruff/black handles automatically

## When to Use This Skill

- **PR review** — Evaluate pull requests or code changes
- **Before major refactoring** — Identify what to fix with a deep scan
- **Code quality audits** — Periodic health checks
- **Pre-release reviews** — Catch issues before production
- **After rapid development** — Clean up AI-generated code

## Common Mistakes

**Don't:** Flag every minor issue as critical, ignore context when evaluating patterns, nitpick formatting that linters handle, try to fix everything immediately

**Do:** Prioritize based on impact, suggest concrete fixes, consider trade-offs, focus on high-value findings first
