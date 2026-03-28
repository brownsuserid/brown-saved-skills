---
name: planning-features
description: Creates comprehensive feature implementation plans when designing new functionality. Combines detailed technical planning with architectural review through scalability, reliability, cost, fitness-for-purpose, and code health lenses before implementation begins. Use this skill whenever the user wants to plan, design, scope, or architect a new feature — even if they don't explicitly say "plan." Also triggers for "how should we build X", "what's the approach for Y", "scope this out", "let's think through how to implement Z", or "where do we start with this feature." Do NOT use for implementing already-planned features (use dev-implementing-features instead) or for bug fixes, refactoring, or code review.
---

# Feature Planning Skill

This skill creates implementation plans that are detailed enough for autonomous execution. Plans use **pseudocode** to show the approach — full implementation follows coding standards during the implementation phase.

Why pseudocode instead of real code? Because planning is about the *approach*, not the syntax. Pseudocode keeps the focus on architecture, data flow, and integration points without getting distracted by type hints, imports, and formatting. The coding standards in `dev-shared-references/coding-standards.md` get applied during implementation, not planning.

## Process Overview

Use the TodoWrite tool to track progress through these six phases:

---

## Phase 1: Initial Planning & Research

The goal of this phase is to understand the problem deeply enough to plan a good solution. Rushing past this into Phase 2 leads to plans that miss edge cases or fight the existing architecture.

### 1.1 Brainstorm & Research

- Brainstorm specific steps to accomplish the stated project
- Identify and recommend the best libraries for the task
- Conduct web research for best libraries, approaches, infrastructure and current best practices
- Review existing code to understand integration points with current system

### 1.2 Clarify Requirements

Ask clarifying questions about:
- Expected behavior and edge cases
- Performance requirements
- Integration points with existing systems
- User experience expectations
- Scalability needs
- Security considerations

**Only proceed to Phase 2 after gaining full clarity.** Ambiguity at this stage becomes costly rework later — every unresolved question is a decision the implementer will make without context.

---

## Phase 2: Create Detailed Plan

Create a comprehensive plan following the structure in `references/planning-best-practices.md`.

### Definition of Done (Required — Goes First)

Every plan must start with a concrete Definition of Done. This is what makes plans safe for autonomous execution — without it, there's no objective way to know when the feature is complete.

The DoD must describe **observable behavior**, not implementation tasks. Each criterion must be verifiable with a yes/no answer.

```markdown
## Definition of Done

> **Lead Developer Review:** Before approving this plan for autonomous execution,
> verify each item below is specific, testable, and represents the complete scope.

### Feature Completion Criteria
- [ ] [Specific user action] results in [specific observable outcome]
- [ ] [API endpoint/function] accepts [specific inputs] and returns [specific outputs]
- [ ] [Error condition] displays [specific error message/behavior]

### Acceptance Scenarios
1. **Scenario: [Name]**
   - Given: [Specific precondition with concrete values]
   - When: [User/system action]
   - Then: [Observable result with exact values]

### Out of Scope (Explicitly)
- [Thing that will NOT be included]

### Quality Gates (Automated)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No linting/type/security errors
- [ ] Test coverage >= 90% for new code
```

**Examples of good vs bad criteria:**

| Bad (Vague) | Good (Specific) |
|-------------|-----------------|
| "User can log in" | "User enters email/password on /login, receives JWT token, is redirected to /dashboard" |
| "Handle errors gracefully" | "Invalid email format shows 'Please enter a valid email address' below the input field" |
| "API works correctly" | "POST /api/users with valid payload returns 201 and user object with id, email, created_at" |

### Plan Must Include (in order):

1. **Definition of Done** — at the very top (see template above)
2. **Overview** — Feature summary, business value, success criteria
3. **Setup** — Git worktree creation using `~/scripts/wt.sh` (this creates a physical worktree so development happens in an isolated directory, not just a branch)
4. **Test-Driven Development** — Unit tests created BEFORE implementation
5. **Implementation with Pseudocode** — Show approach, not full code
6. **Observability & Structured Logging** — JSON logging, correlation IDs, metrics, alarms
7. **Code Quality Checks** — language-appropriate linting, formatting, type checking, and security scanning (for Python projects: ruff check, ruff format, mypy, bandit)
8. **Integration Testing** — End-to-end validation
9. **Documentation** — Updates to relevant docs
10. **User Testing** — Clear scenarios for lead developer testing
11. **Commit & PR** — Only after all tests pass and lead developer approves

### Create Architecture Diagrams

Include Mermaid diagrams in the plan to visualize the feature's architectural impact:

- **Component diagram** — show how the new feature fits into the existing system
- **Data flow diagram** — trace how data moves through the feature
- **Sequence diagram** — for API interactions or multi-service workflows

Diagrams serve dual purpose: human documentation AND AI context-loading for implementation.

**Standards:** See `../dev-shared-references/architecture-diagrams.md` for diagram type selection, templates, and best practices.

### Key Planning Principles

- **Use pseudocode** to illustrate the approach (see `references/planning-best-practices.md` for examples)
- **Be specific** about libraries, file organization, and HOW to implement
- **Reference implementation standards** that will be applied during coding:
  - `../dev-shared-references/coding-standards.md` — Language-specific standards, type hints, docstrings
  - `../dev-shared-references/git-conventions.md` — Commit message format
  - `../dev-shared-references/uv-guide.md` — Dependency management (Python)
  - `../dev-shared-references/aws-standards.md` — AWS infrastructure (if applicable)

### Use the Template

Reference `templates/feature-plan-template.md` for the complete structure to follow.

---

## Phase 3: Anti-Pattern Scan

Before reviewing the plan architecturally, scan the code areas the plan will modify for existing problems. New features built on unhealthy code inherit that debt — it's cheaper to identify issues now than debug mysterious failures later.

### Process

1. Identify the files and modules the plan will modify or extend
2. Run `dev-reviewing-code` in Deep Scan mode on those code areas
3. Document findings: error swallowing, duplication, tight coupling, superficial tests
4. Decide for each finding: fix as part of this plan, or explicitly defer (add to Out of Scope)

Include the scan results in the plan's **Code Health** section under the Architectural Review.

---

## Phase 4: Architectural Review

Now **behave as a senior architect** and review the plan. The planner is naturally biased toward their own design — this phase deliberately shifts perspective to stress-test the plan through lenses the planner may have deprioritized.

### Review Process

1. Read the plan thoroughly
2. Review existing architecture and code to understand the system context
3. Review the anti-pattern scan results from Phase 3
4. Ask clarifying questions if needed
5. Evaluate the plan through each architectural lens (details in `references/architectural-principles.md`)
6. Suggest revisions to improve plan quality

### The Five Architectural Lenses

1. **Scalability & Operability** — What happens at 10x/100x scale? Can we debug this at 3 AM?
2. **Reliability & Resilience** — What's the single point of failure? What happens when downstream services go down?
3. **Cost Optimization** — Are we paying for idle resources? What are the hidden operational costs?
4. **Fitness for Purpose** — Are we using the right tools for the job? What trade-offs are we making?
5. **Code Health** — Incorporate Phase 3 scan results. Are there existing anti-patterns the plan should address or avoid propagating?

For detailed questions to ask for each lens, read `references/architectural-principles.md`.

For AWS infrastructure cost analysis, use `infra-auditing-aws-spending` skill.

### Make Trade-offs Explicit

Frame architectural decisions as explicit trade-offs:
- "We are choosing Pattern A, which gives us [benefit], but we are accepting the trade-off of [cost/limitation]"
- Document these in the plan's "Trade-offs & Decisions" section

---

## Phase 5: Test & Autonomous Execution Review

This phase ensures the plan is **safe for autonomous execution** — meaning Claude can implement it without human intervention and the lead developer can objectively verify completion.

Why a separate phase? Because planning and test specification are different mindsets. Phase 2 focuses on *what* to build; this phase focuses on *how to prove it works*. Plans that skip this step tend to have vague tests like "handles errors gracefully" that pass whether the implementation is correct or not.

### 5.1 Review Definition of Done

Verify each criterion in the Definition of Done is specific enough for autonomous execution:

**Red flags that block autonomous execution:**
- "Works correctly" — What does "correctly" mean?
- "Handles errors" — Which errors? What handling?
- "Handles errors gracefully" — Often leads to error-swallowing patterns. Specify: which errors, what recovery, does it re-raise?
- "User can do X" — What are the exact steps and outcomes?
- "Supports Y" — What does support look like?
- No acceptance scenarios
- Missing out-of-scope section

### 5.2 Enhance Test Specifications

For each test in the plan, verify it has:

**Specificity:**
- Concrete input values (not "valid input" but `email="test@example.com"`)
- Exact expected outputs
- Descriptive test name (`test_[what]_[scenario]_[expected_behavior]`)

**Required test categories:**
- **Happy path** — Normal expected usage with specific values
- **Edge cases** — Boundary values, empty inputs, None, unicode, large inputs
- **Error cases** — Invalid inputs with specific exception types and messages
- **Error propagation** — Verify exceptions propagate (not silently caught); no default returns (`[]`, `None`, `{}`) that mask failures

### 5.3 Test Independence

Add verification steps to the plan:
```
Run tests in isolation: pytest tests/test_file.py::test_specific -v
Run tests in random order: pytest --random-order
Run full suite multiple times to check for flakiness
```

### 5.4 Autonomous Execution Safety Checklist

Add this checklist as a named section in the plan (## Autonomous Execution Safety Checklist). Walk through each item and mark it checked. If any item fails, fix the plan before proceeding.

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

## Phase 6: Finalize & Save Plan

### 6.1 Present to User

- Share the detailed plan with **pseudocode** (not full implementation code)
- Show most important algorithmic approaches
- Explain key architectural decisions and trade-offs
- Walk through the Definition of Done and test specifications
- Get user approval

### 6.2 Save Approved Plan

After user approval:
- Add the exact approved, detailed, and unmodified plan to `PROJECT_ROOT/plans/[feature-name]-plan.md`
- Use the template structure from `templates/feature-plan-template.md`
- This becomes the reference document for implementation

---

## Supporting Files Reference

This skill includes comprehensive reference materials:

### Planning & Process (Skill-Specific)
- `references/planning-best-practices.md` — What makes a good plan, pseudocode examples, plan quality checklist
- `references/architectural-principles.md` — The 5 lenses with detailed questions
- `templates/feature-plan-template.md` — Complete plan structure template

### Implementation Standards (Shared across all dev-* skills)
Applied DURING implementation, not planning:
- `../dev-shared-references/coding-standards.md` — Language-specific standards, type hints, docstrings, testing
- `../dev-shared-references/git-conventions.md` — Commit message format and workflow
- `../dev-shared-references/uv-guide.md` — Dependency management with uv (Python)
- `../dev-shared-references/aws-standards.md` — AWS infrastructure best practices (if applicable)
- `../dev-shared-references/architecture-diagrams.md` — Mermaid diagram standards and templates

### Cross-Skill Integration
- `dev-reviewing-code` — Run Deep Scan mode during Phase 3 Anti-Pattern Scan
- `infra-auditing-aws-spending` — Use during Phase 4 Cost Optimization review (AWS projects)
- `dev-implementing-features` — Use after this skill to execute the approved plan
- `dev-writing-unit-tests` — Comprehensive unit testing patterns (referenced in Phase 5)

---

## Key Principles

- **Plans use pseudocode:** Show the approach without full implementation details
- **Definition of Done first:** Every plan starts with concrete, observable completion criteria
- **Test-driven:** Tests are planned before implementation, with specific inputs and outputs
- **Architecturally rigorous:** Every plan survives scrutiny through all five lenses
- **Autonomous-execution safe:** Plans are specific enough for Claude to implement without human intervention
- **Standards-aware:** Plans reference where implementation standards are documented
- **User-approved:** Get explicit approval before saving the plan
- **Trade-offs explicit:** Document what we're choosing and what we're accepting
