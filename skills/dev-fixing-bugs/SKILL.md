---
name: fixing-bugs
description: Diagnoses and resolves bugs when encountering errors, test failures, or unexpected behavior. Uses test-driven development to validate root cause and ensure all quality gates pass before completion.
---

# Bug Fixing Skill

This skill provides a comprehensive, systematic approach to diagnosing and resolving bugs through test-driven development and thorough validation.

## Process Overview

Use the TodoWrite tool to track progress through these seven phases:

---

## Phase 1: Collect Precise Context

Gather all relevant information about the bug:

### Essential Information
- **Error messages**: Complete error text, stack traces, logs
- **Reproduction steps**: Exact steps to trigger the bug
- **Environment details**: Where it occurs (dev/staging/prod, OS, versions)
- **Expected vs actual behavior**: What should happen vs what happens

### Identify the Environment

Bugs behave differently depending on where they occur. Before investigating, establish which environment the bug is in and collect context from the right place:

- **Local development**: Use local logs, debugger, and unit tests to reproduce
- **Deployed AWS infrastructure** (Lambda, Step Functions, API Gateway): Pull logs and configuration from the deployed environment using `infra-cloudwatch-investigation` — see `../infra-cloudwatch-investigation/SKILL.md`. Common AWS-specific issues include Lambda credential caching (cold start), Secrets Manager access failures, IAM permission gaps, and environment variable misconfiguration
- **CI/CD pipeline**: Check pipeline logs and ensure the CI environment matches expectations (AWS profiles, env vars, permissions)

If the bug only reproduces in a deployed environment, don't waste time trying to reproduce it locally — go straight to CloudWatch logs and deployed resource configuration.

### Investigation Tools
- **Grep**: Pinpoint affected files and dependencies using exact terms (function names, error messages)
- **Task (Explore)**: For broader context gathering across the codebase
- **Read**: Examine specific files with line numbers
- **Subagents:** Spawn parallel `Agent(Explore)` to investigate multiple areas at once (source code, tests, config)
- **CloudWatch investigation**: For bugs in deployed AWS infrastructure, use `../infra-cloudwatch-investigation/SKILL.md` to pull and analyze logs from the correct environment

### Context Mapping
- Trace the data flow or execution path to define the issue's boundaries
- Map inputs, outputs, and interactions
- Identify affected components and dependencies
- Check `docs/architecture/` for existing Mermaid diagrams to understand component relationships and data flows through affected areas (see `../dev-shared-references/architecture-diagrams.md`)

---

## Phase 2: Investigate Root Causes

Trace the bug backward through the call stack to find where it originated, then generate and test hypotheses.

### What "Root Cause" Means

A root cause is the earliest point in the system where a change would have prevented the bug entirely. It's the difference between "where the error appeared" and "where things first went wrong." You know you've found root cause when you can answer yes to all three of these questions:

1. **Origin test**: "Is this the earliest point where the problem could have been prevented?" If you can trace further back to an earlier decision, input, or missing check that would have avoided the issue, you haven't found root cause yet.

2. **Sufficiency test**: "If I fix only this point, does the bug become impossible — not just unlikely?" A fix at the symptom might suppress the error today but leave the door open for the same class of bug tomorrow. A root cause fix closes that door.

3. **Explanation test**: "Can I explain the complete chain from this point to the observed symptom?" If there are gaps in your explanation — steps you're guessing about rather than tracing — you may be looking at a contributing factor rather than the root cause.

When the answer to any of these is "no" or "I'm not sure," keep tracing.

### Systematic Call Stack Tracing

Bugs often manifest deep in the call stack, but fixing where errors appear merely treats symptoms. Trace backward to find the original trigger.

**Step 1 - Document the Symptom:**
- Record the exact error message and location where it manifests
- Note the specific operation that failed
- This is your starting point, not your destination

**Step 2 - Find the Immediate Cause:**
- Locate the exact code (function/line) executing when the crash occurs
- This is often NOT the root cause — it's where the problem became visible

**Step 3 - Navigate Upward Through the Call Chain:**
- Ask: "What called this function?"
- Track parameter values passed through the call chain
- Look for invalid or unexpected data at each level
- Use stack traces to map the complete execution path

**Step 4 - Recursive Tracing:**
- Continue moving up the call hierarchy
- At each level, ask: "What called this?" and "Where did this data come from?"
- Keep tracing until no further callers exist or you find where valid data became invalid

**Step 5 - Identify the Origin Point:**
- Find where invalid data originated or where a missing check should have existed
- Check initialization, test setup, or environmental conditions
- Apply the three root cause tests above — if any answer is "no," keep tracing

### Generate Multiple Hypotheses

After tracing the call stack, list **at least 3 plausible root causes** spanning:
- Code logic errors at the origin point
- Invalid data from initialization or setup
- Dependency issues
- Configuration problems
- Race conditions
- Data validation failures at entry points

### Validate Each Hypothesis
- Use Read tool to inspect code with line numbers
- Cross-reference execution paths and dependency chains
- Gather evidence for and against each hypothesis
- Confirm or rule out systematically before proceeding
- **Subagents:** Validate multiple hypotheses in parallel — one `Agent(Explore)` per hypothesis

### Document Your Investigation
For each hypothesis, record:
- Evidence supporting it
- Evidence against it
- How you tested it (including call stack levels traced)
- Conclusion (confirmed/ruled out) with reasoning

For the confirmed root cause, explicitly document the three verification tests:
- **Origin**: Why this is the earliest point where the bug could have been prevented
- **Sufficiency**: Why fixing this point makes the bug impossible, not just unlikely
- **Explanation**: The complete chain from this point to the observed symptom

**Detailed investigation techniques:** See `references/root-cause-analysis.md`

---

## Phase 3: Reuse Existing Patterns

Before implementing a fix, check if similar issues have been solved before.

### Search for Prior Solutions
- Use Grep to search for similar error messages or bug patterns
- Look for existing error handling utilities
- Find tests that handle similar edge cases
- Review git history for related fixes
- **Subagents:** Use `Agent(Explore)` to search git history for similar fixes while you continue analysis

### Identify Reusable Patterns
- Error handling strategies already in codebase
- Validation utilities that could be applied
- Testing patterns for similar scenarios

### Validate Applicability
- Ensure the existing pattern fits your specific bug
- Don't force-fit a solution that doesn't match
- Follow project conventions and established patterns

---

## Phase 4: Analyze Impact

Before implementing the fix, understand its full scope and impact.

### Trace Dependencies
- Map all affected dependencies (imports, calls, external services)
- Identify integration points that might be affected
- Check for cascade effects on dependent systems
- **Subagents:** Trace upstream callers, downstream consumers, and test coverage in parallel via `Agent(Explore)`

### Assess Scope
- Is this a localized bug or symptom of broader design flaw?
- Could this indicate issues like tight coupling or missing error handling?
- Are other areas of the system affected by the same root cause?
- If this area has required repeated fixes or the same issue keeps resurfacing, consider running the **refactoring skill** (`dev-refactoring`) to address underlying structural problems before patching again.

### Evaluate Side Effects
- How will the fix impact performance?
- Will it affect other features or use cases?
- Are there any breaking changes?
- What's the migration path if needed?

---

## Phase 5: Share Top Hypotheses

Before implementing any fix, present your findings to the lead developer for alignment.

### Present Your Top 3 Hypotheses

Share the **top 3 most likely root causes** ranked by confidence, including:

1. **Hypothesis name** - A clear, concise label
2. **Evidence supporting it** - What you found that points to this cause
3. **Evidence against it** - What doesn't fit or is uncertain
4. **Confidence level** - High / Medium / Low
5. **Root cause verification** - For your top hypothesis, explain how it passes the three tests: Is this the earliest preventable point? Would fixing it make the bug impossible? Can you trace the complete chain to the symptom?
6. **Proposed fix approach** - How you would address it if confirmed

### Recommend a Path Forward

- Identify which hypothesis you recommend investigating first and why
- Highlight any risks or unknowns that need clarification
- Note if multiple hypotheses could be contributing (compound bugs)

### Get Alignment

- Wait for the lead developer to confirm or redirect before proceeding to implementation
- If the lead developer identifies a different root cause, revisit Phase 2
- Document the agreed-upon approach before moving forward

**Do NOT proceed to Phase 6 without lead developer alignment.**

---

## Phase 6: Test-Driven Fix with Multi-Layer Defense

Implement the fix using a test-driven approach with validation at multiple architectural layers.

### Create/Update Tests FIRST
- Update existing test or create new test that reproduces the bug
- Test should FAIL before the fix, PASS after the fix
- Add tests for edge cases related to the bug
- Tag integration tests with `@pytest.mark.integration`

### Implement Multi-Layer Defense Strategy

Rather than fixing at a single point, implement validation at multiple layers to prevent recurrence.

**Identify validation layers:**
1. **Origin point** - Where data is created or entered the system
2. **Intermediate functions** - Where data is passed through or transformed
3. **Usage point** - Where the bug manifested
4. **Type system** - Use types to enforce constraints
5. **Test coverage** - Ensure bug cannot recur

**Example: Empty directory parameter bug**
- Layer 1: Validate at getter that returns directory path
- Layer 2: Validate in initialization function that receives path
- Layer 3: Guard at git command execution point
- Layer 4: Use Path types instead of strings
- Layer 5: Add tests for empty/invalid directories

**Complete multi-layer defense guide:** See `references/root-cause-analysis.md` - "Multi-Layer Defense Strategy"

### Implement Minimal, Targeted Fix
- Focus on resolving the root cause at its origin
- Add defensive guards at architectural boundaries
- Make smallest changes that fix the issue completely
- Avoid scope creep (no "while I'm here" changes)
- Provide specific file paths and line numbers for all changes

### Document the Fix
- Add inline comments explaining non-obvious fixes
- Update docstrings if function behavior changed
- Explain WHY the fix works, not just WHAT changed
- Document assumptions at component boundaries

### Follow Implementation Standards
All code changes must follow standards in:
- `../dev-shared-references/coding-standards.md` - Type hints, docstrings, error handling
- `../dev-shared-references/git-conventions.md` - Commit message format
- `../dev-shared-references/uv-guide.md` - Dependency management (if adding deps)

---

## Phase 7: Validate and Monitor

Ensure the fix is complete and ready for deployment through comprehensive validation.

### Stop Hook Automation
The Stop hook automatically runs after every turn:
- ✅ Unit tests (`pytest -m "not integration"`)
- ✅ Type checking (`mypy`)
- ✅ Linting (`ruff check --fix`)
- ✅ Formatting (`ruff format`)

### Additional Required Checks
These are NOT covered by the Stop hook:

```bash
# Integration tests (requires .env)
cd [PROJECT_ROOT] && set -a && source .env && set +a && PYTHONPATH=. uv run pytest -m integration -v

# Security scanning
bandit -c pyproject.toml -r .
```

### Quality Checklist
- [ ] Stop hook passing (unit tests, mypy, ruff)
- [ ] Integration tests pass
- [ ] Security scan passes (bandit)
- [ ] Lead developer has tested the fix
- [ ] Commit message explains root cause and fix

**Detailed validation requirements:** See `references/validation-requirements.md`

### Present a Fix Summary

After implementing the fix, present a clear summary to the developer in chat. This is how you communicate what you found — don't just silently fix code. Include:

1. **Root Cause**: Where and why things first went wrong (the origin point, not the crash site)
2. **Propagation Chain**: How the root cause led to the observed symptom
3. **What Was Fixed**: What you changed and why, with file paths
4. **Tests Added**: What new tests verify the fix
5. **Verification**: Why this fix addresses the root cause (not just the symptom)

Keep it concise — a few paragraphs, not a wall of text. The goal is to give the developer enough context to understand and validate the fix.

### Recommend Monitoring
Suggest monitoring to prevent recurrence:
- Logs or metrics to track if issue returns
- Alerts for similar error patterns
- Performance monitoring if relevant

---

## Supporting Files Reference

This skill includes comprehensive reference materials:

### Bug-Fixing Specific
- `references/root-cause-analysis.md` - Investigation techniques, common bug patterns, hypothesis generation
- `references/validation-requirements.md` - Complete quality gates checklist, validation workflow
- `templates/bug-fix-report.md` - Template for documenting the fix

### Related Skills
- `../infra-cloudwatch-investigation/SKILL.md` - Debug AWS production issues (Lambda/Step Function failures) via CloudWatch logs
- `../dev-reviewing-code/SKILL.md` - When bug reveals systemic issues, use Deep Scan mode to scan for broader anti-patterns

### Implementation Standards (Shared across all dev-* skills)
- `../dev-shared-references/coding-standards.md` - Python best practices, type hints, docstrings, testing
- `../dev-shared-references/git-conventions.md` - Commit message format and workflow
- `../dev-shared-references/uv-guide.md` - Dependency management with uv
- `../dev-shared-references/aws-standards.md` - AWS infrastructure best practices

---

## Key Principles

- **Systematic investigation:** Test multiple hypotheses, don't jump to conclusions
- **Test-driven:** Write/update tests BEFORE implementing fix
- **Minimal changes:** Fix the bug, avoid refactoring or scope creep
- **Thorough validation:** ALL quality gates must pass
- **Root cause focus:** Fix the cause, not just symptoms
- **Documentation:** Explain WHY the fix works for future maintainers

## Success Criteria

- Root cause identified and validated through systematic investigation
- Fix implemented with minimal, targeted changes
- Tests created/updated proving the fix works
- Stop hook passing (unit tests, mypy, ruff)
- Integration tests passing
- Security scan passing (bandit)
- Lead developer tested and approved
- Commit created with detailed message (pushed to branch, not main)
- Bug fix report documents the investigation and resolution
