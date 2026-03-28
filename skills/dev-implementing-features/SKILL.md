---
name: implementing-features
description: Implements new features or functionality using test-driven development when ready to write code based on a plan or requirements. Follows Red-Green-Refactor cycle, ensures all quality gates pass, and creates proper commits with PRs. Use this skill whenever a developer says "build this", "implement this feature", "code this up", "let's start coding", "write the code for", "add this functionality", or has a plan file ready to execute. Also triggers when the user wants to follow TDD, needs help with the red-green-refactor cycle, or asks to turn a feature plan into working code. If a plan exists in plans/, this is the skill to execute it.
---

# Implementing Features Skill

Tests are the AI's feedback loop. Without them, you're guessing whether the code works. With them, you know. This skill follows test-driven development because writing tests first forces you to design the interface before the implementation — and gives you immediate, automated validation that the code does what it should.

## Process Overview

Use the TodoWrite tool to track progress through these phases:

---

## Phase 1: Preparation

Gather context and ensure you have the latest code before starting implementation.

### Read the Plan (if applicable)

If implementing from a feature plan:
```bash
# Plans should be in PROJECT_ROOT/plans/
cat plans/[feature-name]-plan.md
```

Review the plan for: feature requirements, acceptance criteria, implementation approach, libraries to use, file structure, and test scenarios.

### Review Implementation Standards

Read the shared standards that apply to all implementation work:
- `../dev-shared-references/coding-standards.md` - Python standards, type hints, docstrings
- `../dev-shared-references/git-conventions.md` - Git workflow and commit format
- `../dev-shared-references/uv-guide.md` - Dependency management

These standards exist because consistency across the codebase makes code easier to read, review, and maintain — especially when AI agents are contributing alongside humans.

### Get Latest Code

```bash
git fetch origin
git rebase origin/main
```

### Review Architecture Diagrams

Before writing code, check `docs/architecture/` or the project README for existing diagrams. Understand how the component you're modifying fits into the system and identify upstream/downstream dependencies. Note any diagrams that will need updating after your changes.

Standards: `../dev-shared-references/architecture-diagrams.md`

---

## Phase 2: Branch Setup

Create an isolated environment so your work doesn't affect the main branch until it's validated.

### Check Current Environment

```bash
git worktree list
git branch --show-current
```

### Create Feature Branch

If not already in a worktree:

```bash
# For new feature
git checkout -b feature/[feature-name]

# For bug fix
git checkout -b fix/[bug-name]

# For refactoring
git checkout -b refactor/[description]
```

Or use the user's worktree script:
```bash
~/scripts/wt.sh feature/[feature-name]
```

Working directly on main means any mistake is immediately in the shared branch — feature branches give you space to experiment and validate before merging.

---

## Phase 3: Write Tests First (TDD)

Write failing tests BEFORE implementing code. This feels counterintuitive, but it's the most reliable way to ensure you build exactly what's needed — no more, no less.

### The Red-Green-Refactor Cycle

**1. RED — Write a failing test:**
```python
# tests/test_[module].py

def test_function_with_valid_input_returns_expected_output():
    """Test that function works with normal input."""
    # Arrange
    input_data = "test"
    expected = "EXPECTED_RESULT"

    # Act
    result = function_to_implement(input_data)

    # Assert
    assert result == expected
```

**Run the test — it should FAIL:**
```bash
pytest tests/test_[module].py -v
```

Expected: `ModuleNotFoundError` or `ImportError` (function doesn't exist yet)

**2. GREEN — Write minimal code to make it pass**

**3. REFACTOR — Improve while keeping tests green**

### Why Tests First?

- **Design:** Forces you to think about the API/interface before getting lost in implementation details
- **Confidence:** Tests prove the code works — not just that it runs without errors
- **Documentation:** Tests show exactly how code should be called
- **Regression prevention:** Future changes won't silently break functionality
- **Refactoring safety:** Can improve code structure with confidence

For detailed TDD patterns, edge case strategies, and troubleshooting: `references/implementation-workflow.md`

---

## Phase 4: Implement Code

Write minimal code to make the tests pass. Resist the urge to build ahead of what the tests require.

### Follow Coding Standards

Requirements from `coding-standards.md`:
- Type hints on all function parameters and returns
- Google-style docstrings with Args, Returns, Examples
- Proper error handling with specific exceptions
- Async/await for I/O operations

**Example:**
```python
from typing import Optional

def function_name(param: str, optional: Optional[int] = None) -> str:
    """Brief one-line description.

    Detailed explanation of what the function does and why.

    Args:
        param: Description of param
        optional: Description of optional parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When input is invalid

    Examples:
        >>> function_name("input")
        "output"
    """
    if not param:
        raise ValueError("param cannot be empty")

    result = process(param)
    return result
```

### Run Tests — Should Pass Now

```bash
pytest tests/test_[module].py -v
```

### Iterate: Red-Green-Refactor

1. Write test for edge case → Run (RED - FAIL)
2. Implement edge case handling → Run (GREEN - PASS)
3. Write test for error case → Run (RED - FAIL)
4. Implement error handling → Run (GREEN - PASS)
5. Refactor if needed → Tests still GREEN

---

## Phase 5: Validate Quality

### Stop Hook Automation
The Stop hook automatically runs after every turn:
- Unit tests (`pytest -m "not integration"`)
- Type checking (`mypy`)
- Linting (`ruff check --fix`)
- Formatting (`ruff format`)

Check the Stop hook output for any failures before proceeding.

### Additional Required Checks
These are NOT covered by the Stop hook:

```bash
# Integration tests (requires .env)
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v

# Security scanning
bandit -c pyproject.toml -r .
```

Integration tests tagged with `@pytest.mark.integration` verify that components work together with real dependencies — unit tests alone can't catch integration issues.

If security issues are found, fix them and re-run integration tests.

### Anti-Pattern Scan

Run `dev-reviewing-code` in Deep Scan mode on the files you modified or created. This catches issues that linting and tests miss: error swallowing, tight coupling, duplication, and superficial tests. Fix any findings before proceeding.

---

## Phase 6: Update Architecture Diagrams

After implementation is validated, update diagrams to reflect what was actually built.

### When to Create or Update Diagrams

Create or update diagrams when your implementation:
- Adds new components, services, or modules
- Changes data flows or API interactions
- Modifies system boundaries or external integrations
- Alters database schemas or data models

### Save Diagrams

```bash
mkdir -p docs/architecture/
```

Save diagrams as Markdown files with embedded Mermaid in `docs/architecture/`:
- One primary concept per file (e.g., `user-auth-flow.md`, `data-pipeline.md`)
- Include a text description above each diagram explaining what it shows

Update the project README with an `## Architecture` section linking to the diagrams.

Standards: `../dev-shared-references/architecture-diagrams.md`

---

## Phase 7: Deploy to Dev

Deploy to the development environment for testing. The process depends on your project's infrastructure.

### Pre-Deployment Checklist

Before deploying, verify:
- All quality gates passed (Phase 5)
- Code committed to feature branch
- Environment variables configured in dev
- Database migrations ready (if applicable)

### Deployment Process

**For AWS CDK projects:** See `references/cdk-direct-deployment.md` for comprehensive guidance including environment setup, stage naming, customer-specific deployments, and troubleshooting.

**Quick CDK reference:**
```bash
cd PROJECT_ROOT/cdk

export CDK_DEFAULT_ACCOUNT=YOUR_ACCOUNT_ID
export CDK_DEFAULT_REGION=us-east-1
export AWS_PROFILE=YOUR_AWS_PROFILE
export PYTHONPATH="$(dirname $(pwd))"

npx cdk deploy "STAGE_NAME/*" \
  --require-approval never \
  --context environment=ENVIRONMENT \
  --context customer=CUSTOMER \
  --profile YOUR_AWS_PROFILE
```

### Post-Deployment Verification

After deployment:
- Service health check passes
- Database migrations applied successfully
- API endpoints responding correctly
- No errors in logs
- Monitoring/metrics active

### Live AWS Tests (Optional)

For AWS infrastructure changes (Lambda, Step Functions, API Gateway), run live tests against deployed resources:

```bash
export TEST_EMAIL_RECIPIENT=your@email.com
export TEST_SENDER_ALIAS=your-alias

uv run pytest tests/live_aws/ -v -m live_aws -k "${FEATURE_NAME}"
```

See `../dev-testing-live-aws/SKILL.md` for complete guidance.

### If Deployment Fails

1. Review deployment logs — identify the failure point
2. Rollback if needed — restore previous working version
3. Fix the issue — may need to return to Phase 4 or 5
4. Re-run quality checks
5. Re-deploy

---

## Phase 8: User Validation

The lead developer tests and approves the implementation in the dev environment before any code gets merged.

### Provide Testing Instructions

Create clear testing scenarios:

**Feature:** [Feature Name]
**Dev Environment URL:** [relevant endpoint]

**Testing Scenarios:**

1. **Happy Path:**
   - Steps: [1, 2, 3...]
   - Expected: [What should happen]

2. **Edge Case:**
   - Steps: [1, 2, 3...]
   - Expected: [What should happen]

3. **Error Handling:**
   - Steps: [Trigger error condition]
   - Expected: [Graceful error handling]

### Get Approval

- Ask user to test the implementation in the dev environment
- Wait for explicit approval before proceeding to Phase 9
- Address any issues found — may need to loop back to Phase 4

---

## Phase 9: Commit & Push

Save work and create a pull request for review.

Follow the complete git/PR workflow in `../dev-shared-references/git-and-pr-workflow.md`, including commit message formats, PR templates, and version bumping guidance. Also see `../dev-shared-references/semantic-versioning.md`.

---

## Supporting Files Reference

### Implementation-Specific
- `references/implementation-workflow.md` - Deep TDD patterns, troubleshooting common issues
- `references/cdk-direct-deployment.md` - Direct CDK deployment commands for multi-customer AWS deployments

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Python best practices, type hints, docstrings
- `../dev-shared-references/git-conventions.md` - Commit message format and workflow
- `../dev-shared-references/uv-guide.md` - Dependency management with uv
- `../dev-shared-references/architecture-diagrams.md` - Mermaid diagram standards and templates

### Related Skills
- `../dev-reviewing-code/SKILL.md` - Code review with Deep Scan mode for anti-pattern detection (Phase 5)
- `../dev-testing-live-aws/SKILL.md` - Live AWS infrastructure testing
- `../infra-cdk-quality/SKILL.md` - CDK infrastructure quality validation
- `../dev-writing-integration-tests/SKILL.md` - Integration test creation with Testcontainers
- `../dev-reviewing-code/SKILL.md` - Self-review before PR submission

---

## Workflow Checklist

Before committing, verify:

- [ ] Plan reviewed (if applicable)
- [ ] Standards reviewed (coding, git, uv)
- [ ] Latest code fetched and rebased
- [ ] Branch created for feature
- [ ] Tests written first (TDD)
- [ ] Implementation follows coding-standards.md
- [ ] Stop hook passing (unit tests, mypy, ruff)
- [ ] Integration tests pass
- [ ] Anti-pattern scan passes on changed files
- [ ] Security scan passes (bandit)
- [ ] Architecture diagrams created/updated (if applicable)
- [ ] Deployed to dev environment (if applicable)
- [ ] Live AWS tests pass (if AWS infrastructure changed)
- [ ] Lead developer tested and approved
- [ ] Commit message follows git-conventions.md
- [ ] Pushed to feature branch (not main)
- [ ] PR created with detailed description

---

## Key Principles

- **Test-Driven Development:** Red → Green → Refactor. Tests are the feedback loop that tells you whether the code works
- **Quality Gates:** All tests + type checking + security + linting pass before merging — catching issues early is cheaper than catching them in production
- **Standards Adherence:** Consistency makes code readable and reviewable across human and AI contributors
- **User Validation:** The lead developer approves before merging — automated checks catch syntax and logic issues, but humans catch design and UX problems
- **Proper Git Workflow:** Feature branches, descriptive commits, PRs — isolation prevents half-finished work from affecting others
- **Iterative Approach:** Small, incremental changes with continuous validation
