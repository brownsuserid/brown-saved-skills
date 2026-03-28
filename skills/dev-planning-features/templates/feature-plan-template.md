# Feature Plan: [Feature Name]

**Date:** [YYYY-MM-DD]
**Author:** Claude Code
**Status:** Approved

## Table of Contents

- [Definition of Done](#definition-of-done)
- [Overview](#overview)
- [Setup & Preparation](#setup--preparation)
- [Test-Driven Development](#test-driven-development)
- [Implementation Plan](#implementation-plan)
- [Architectural Considerations](#architectural-considerations)
- [Code Quality & Security](#code-quality--security)
- [Integration Testing](#integration-testing)
- [Documentation Updates](#documentation-updates)
- [User Acceptance Testing](#user-acceptance-testing)
- [Commit & Pull Request](#commit--pull-request)
- [Autonomous Execution Safety Checklist](#autonomous-execution-safety-checklist)
- [Trade-offs & Decisions](#trade-offs--decisions)

---

## Definition of Done

> **Lead Developer Review:** Before approving this plan for autonomous execution,
> verify each item below is specific, testable, and represents the complete scope.

### Feature Completion Criteria
- [ ] [Specific user action] results in [specific observable outcome]
- [ ] [API endpoint/function] accepts [specific inputs] and returns [specific outputs]
- [ ] [Error condition] displays [specific error message/behavior]
- [ ] [Edge case scenario] is handled by [specific behavior]

### Acceptance Scenarios
1. **Scenario: [Name]**
   - Given: [Specific precondition with concrete values]
   - When: [User/system action]
   - Then: [Observable result with exact values]

2. **Scenario: [Name]**
   - Given: [Specific precondition with concrete values]
   - When: [User/system action]
   - Then: [Observable result with exact values]

### Out of Scope (Explicitly)
- [Thing that will NOT be included]
- [Future enhancement deferred]

### Quality Gates (Automated)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No linting/type/security errors
- [ ] Test coverage >= 90% for new code

---

## Overview

### Feature Summary
[Brief description of what's being built]

### Business Value
[Why this feature matters to users/business]

### Success Criteria
[How we'll know the feature is complete and working correctly]

---

## Setup & Preparation

### Git Worktree Creation
```
- Create new worktree using ~/scripts/wt.sh
- Branch name: feature/[feature-name]
- Ensures development happens in an isolated directory
```

### Environment Setup
```
[Any environment preparation needed]
- Dependencies to install
- Configuration files to update
- Environment variables needed
```

---

## Test-Driven Development

### Unit Tests (Create BEFORE Implementation)

**File:** `tests/test_[module_name].py`

```
Test Cases:

test_[what]_[scenario]_[expected_behavior]:
    - Given: [specific precondition with concrete values]
    - When: [action performed]
    - Then: [exact expected outcome with specific values]

test_[what]_[edge_case]_[expected_behavior]:
    - Given: [edge condition with concrete values]
    - When: [action performed]
    - Then: [exact expected outcome]

test_[what]_[error_condition]_raises_[exception_type]:
    - Given: [error condition with concrete values]
    - When: [action performed]
    - Then: raises [ExceptionType] with message containing "[expected message]"

test_[what]_[error_propagation]_does_not_swallow:
    - Given: [downstream failure condition]
    - When: [action performed]
    - Then: exception propagates to caller (not silently caught)
```

---

## Implementation Plan

### Libraries & Dependencies

**Primary Libraries:**
- [Library Name]: [Why chosen, what it provides]
- [Library Name]: [Why chosen, what it provides]

**Installation:**
```bash
uv add [library1] [library2]
uv add -D [dev-library1]  # Development dependencies
```

### File Structure

```
[project_root]/
├── [module_path]/
│   ├── [file1].py - [Purpose]
│   ├── [file2].py - [Purpose]
│   └── [file3].py - [Purpose]
└── tests/
    ├── test_[file1].py
    └── integration/
        └── test_[feature]_flow.py
```

### Implementation Steps with Pseudocode

#### Step 1: [Component Name]

**File:** `[file_path]`

**Pseudocode:**
```
function [function_name](param1, param2):
    - [Step 1 description]
    - [Step 2 description]
    - if [condition]:
        - [conditional logic]
    - return [result]

class [ClassName]:
    - attributes: [list attributes]
    - methods:
        - [method_name](): [purpose]
        - [method_name](): [purpose]
```

**Key Logic:**
- [Explain important algorithmic decisions]
- [Explain data flow]
- [Explain integration points]

#### Step 2: [Next Component]

**File:** `[file_path]`

**Pseudocode:**
```
[Pseudocode for next component]
```

**Integration:**
- [How this connects to Step 1]
- [What data flows between components]

[Continue with additional steps as needed]

---

## Architectural Considerations

### Scalability
- [How will this scale with increased load?]
- [Any potential bottlenecks identified?]

### Reliability
- [What are the failure points?]
- [How are errors handled?]
- [What happens if dependencies fail?]

### Cost
- [Infrastructure costs estimated]
- [Operational costs estimated]

### Fitness for Purpose
- [Why these technologies are the right fit]
- [What trade-offs are we making?]

### Code Health
- [Anti-pattern scan results for code areas being modified]
- [Existing issues to address or explicitly defer]
- [Error handling patterns in existing code — swallowing vs propagating?]

### Observability & Structured Logging
- **Log format:** JSON structured logging with correlation IDs
- **Key fields:** `timestamp`, `level`, `service`, `correlation_id`, `customer_id`, `action`, `latency_ms`, `success`
- **What we're logging:**
  - [List significant operations that need audit trail]
  - [List external API calls with latency tracking]
  - [List error scenarios with context capture]
- **Metrics:**
  - [Request count and error rate per operation]
  - [Latency percentiles (P50, P95, P99)]
  - [Business-specific metrics for this feature]
- **Alarms:**
  - [Error rate threshold]
  - [Latency degradation threshold]
- **Sensitive data:** [Confirm no PII, credentials, or tokens are logged]

---

## Code Quality & Security

### Quality Checks (Must Pass Before Commit)

For Python projects:
```
- Run ruff check (linting)
- Run ruff format (code formatting)
- Run mypy (type checking)
- Run bandit (security scanning)
- All unit tests passing
- All integration tests passing
```

For other languages, include equivalent tooling.

### Implementation Standards

Implementation will follow:
- **Language Standards:** `dev-shared-references/coding-standards.md`
  - Type hints on all functions/methods/classes
  - Docstrings on public APIs
  - 90%+ test coverage
  - Proper exception handling

- **Git Conventions:** `dev-shared-references/git-conventions.md`
  - Structured commit messages
  - Never push to main directly

- **Dependency Management:** `dev-shared-references/uv-guide.md` (Python)
  - Use `uv add` for dependencies
  - Commit `uv.lock` for reproducibility

[If AWS is involved:]
- **AWS Standards:** `dev-shared-references/aws-standards.md`
  - [Specific AWS patterns being used]

---

## Integration Testing

### End-to-End Test Scenarios

**File:** `tests/integration/test_[feature]_flow.py`

```
@pytest.mark.integration
test_complete_[feature]_flow():
    - Given: [specific setup with concrete values]
    - When: [sequence of actions]
    - Then: [exact expected end state]

@pytest.mark.integration
test_[feature]_error_handling():
    - Given: [error condition with concrete values]
    - When: [action that triggers error]
    - Then: [specific error behavior — propagation, not swallowing]
```

### Test Independence Verification

```
Run tests in isolation: pytest tests/test_file.py::test_specific -v
Run tests in random order: pytest --random-order
Run full suite multiple times to check for flakiness
```

---

## Documentation Updates

### Files to Update

1. **API Documentation:** `docs/api/[module].md`
   - [What to document]

2. **User Guide:** `docs/guides/[feature].md`
   - [What to document]

3. **README.md**
   - [Update installation instructions]
   - [Update configuration section]
   - [Add feature description]

---

## User Acceptance Testing

### Testing Instructions for Lead Developer

#### Test Scenario 1: [Happy Path]
**Steps:**
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Expected Outcome:**
- [Expected result 1]
- [Expected result 2]

#### Test Scenario 2: [Edge Case]
**Steps:**
1. [Action 1]
2. [Action 2]

**Expected Outcome:**
- [Expected result]

#### Test Scenario 3: [Error Handling]
**Steps:**
1. [Trigger error condition]
2. [Observe behavior]

**Expected Outcome:**
- [Specific error behavior]
- [Exact error message]

---

## Commit & Pull Request

### Prerequisites Checklist
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Quality checks passing (language-appropriate)
- [ ] Lead developer has tested and approved

### Commit Message

```
[type]: [brief description]

[Detailed body paragraph explaining what changes were made, why the
changes were necessary, and any important implementation details.
Reference any relevant issues or tickets.]

-Agent Generated Commit Message
```

### Pull Request

- **Branch:** `feature/[feature-name]`
- **Target:** `main`
- **Reviewers:** [List reviewers]
- **Related Issues:** #[issue-number]

**PR Description:**
```
## Summary
[Brief summary of changes]

## Implementation Details
[Key technical decisions]

## Testing
- Unit tests: [X passing]
- Integration tests: [X passing]
- Manual testing: [Completed by lead developer]

## Documentation
[List documentation updates]

## Breaking Changes
[Any breaking changes, or "None"]
```

---

## Autonomous Execution Safety Checklist

> Walk through each item. If any fails, fix the plan before approving.

- [ ] Definition of Done is at the top of the plan
- [ ] Each completion criterion describes observable behavior with specific values
- [ ] Acceptance scenarios use concrete data (not placeholders)
- [ ] Out of scope section explicitly lists what's NOT included
- [ ] All tests have specific input values and expected outputs
- [ ] Edge cases explicitly documented for each function
- [ ] Error conditions tested with specific exception types and messages
- [ ] Error propagation verified — no silent error swallowing
- [ ] No vague language remains ("works correctly", "handles errors", etc.)
- [ ] No TODO or TBD items remain — everything is decided upfront
- [ ] Lead developer can answer "Is this done?" with yes/no for each criterion

---

## Trade-offs & Decisions

### Key Decisions Made
1. **[Decision]:** [Rationale]
   - Trade-off: [What we're gaining vs. what we're accepting]

2. **[Decision]:** [Rationale]
   - Trade-off: [What we're gaining vs. what we're accepting]

### Alternatives Considered
- **[Alternative Approach]:** [Why not chosen]
- **[Alternative Approach]:** [Why not chosen]

---

## Future Considerations

- [Potential enhancements]
- [Known limitations to address later]
