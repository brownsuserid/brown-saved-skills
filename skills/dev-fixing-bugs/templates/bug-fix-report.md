# Bug Fix Report: [Brief Description]

**Date:** [YYYY-MM-DD]
**Fixed By:** Claude Code
**Issue Reference:** #[issue-number] (if applicable)
**Severity:** [Critical / High / Medium / Low]

---

## Issue Description

### Observed Behavior
[What was actually happening - the bug]

### Expected Behavior
[What should have been happening]

### Impact
[Who/what was affected by this bug]
- User impact: [description]
- System impact: [description]
- Business impact: [description]

### How Discovered
[How was this bug found - user report, automated testing, monitoring, etc.]

---

## Investigation

### Initial Analysis

**Error Messages:**
```
[Paste exact error messages, stack traces, or logs]
```

**Affected Code:**
- File: [file_path:line_number]
- Function/Method: [name]
- Related Files: [list other affected files]

### Hypotheses Tested

#### Hypothesis 1: [Description]
**Evidence For:**
- [Point supporting this hypothesis]
- [Another supporting point]

**Evidence Against:**
- [Point contradicting this hypothesis]
- [Another contradicting point]

**Investigation Steps:**
1. [What you did to test this]
2. [Additional investigation]

**Conclusion:** ✓ CONFIRMED / ✗ RULED OUT

**Reasoning:** [Why you reached this conclusion]

---

#### Hypothesis 2: [Description]
**Evidence For:**
- [Point supporting this hypothesis]

**Evidence Against:**
- [Point contradicting this hypothesis]

**Investigation Steps:**
1. [What you did to test this]

**Conclusion:** ✓ CONFIRMED / ✗ RULED OUT

**Reasoning:** [Why you reached this conclusion]

---

#### Hypothesis 3: [Description]
**Evidence For:**
- [Point supporting this hypothesis]

**Evidence Against:**
- [Point contradicting this hypothesis]

**Investigation Steps:**
1. [What you did to test this]

**Conclusion:** ✓ CONFIRMED / ✗ RULED OUT

**Reasoning:** [Why you reached this conclusion]

---

### Root Cause

**Confirmed Root Cause:**
[Detailed explanation of what was actually wrong]

**Why It Occurred:**
[Explain how this bug came to exist]

**Contributing Factors:**
- [Factor 1]
- [Factor 2]

---

## Fix Applied

### Changes Made

#### File: [path/to/file.py]
**Lines Changed:** [line numbers]

**Before:**
```python
[Code before the fix]
```

**After:**
```python
[Code after the fix]
```

**Rationale:**
[Why this change fixes the issue]

---

#### File: [path/to/another_file.py] (if applicable)
**Lines Changed:** [line numbers]

**Before:**
```python
[Code before the fix]
```

**After:**
```python
[Code after the fix]
```

**Rationale:**
[Why this change was needed]

---

### Why This Fix Works

[Detailed explanation of how the fix addresses the root cause]

### Alternative Approaches Considered

**Alternative 1: [Description]**
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]
- **Why Not Chosen:** [Reason]

**Alternative 2: [Description]**
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]
- **Why Not Chosen:** [Reason]

---

## Testing

### Tests Added/Updated

#### Unit Tests

**File:** `tests/test_[module].py`

**New Tests:**
1. `test_[bug_scenario]()` - Reproduces original bug, verifies fix
2. `test_[edge_case]()` - Tests edge case related to bug
3. `test_[error_handling]()` - Verifies proper error handling

**Updated Tests:**
1. `test_[existing_test]()` - Updated to account for fix

**Test Coverage:**
- Before: [X]%
- After: [Y]%
- Lines Covered: [specific lines]

#### Integration Tests

**File:** `tests/integration/test_[feature]_flow.py`

**Tests:**
1. `test_[end_to_end_scenario]()` - Verifies fix in full system context

---

### Manual Testing Performed

#### Test Scenario 1: Original Bug Reproduction
**Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Before Fix:** [What happened - should fail]
**After Fix:** [What happened - should succeed]
**Result:** ✓ PASS / ✗ FAIL

---

#### Test Scenario 2: Edge Case
**Steps:**
1. [Step 1]
2. [Step 2]

**Expected Outcome:** [What should happen]
**Actual Outcome:** [What actually happened]
**Result:** ✓ PASS / ✗ FAIL

---

#### Test Scenario 3: Regression Check
**Steps:**
1. [Step 1]
2. [Step 2]

**Expected Outcome:** [Verify related functionality still works]
**Actual Outcome:** [What actually happened]
**Result:** ✓ PASS / ✗ FAIL

---

## Validation Results

### Automated Quality Gates

- [x] All unit tests pass (X/X passing)
- [x] All integration tests pass (X/X passing)
- [x] Linting passes (`ruff check`)
- [x] Formatting applied (`ruff format`)
- [x] Type checking passes (`mypy`)
- [x] Security scan passes (`bandit`)
- [x] Test coverage maintained/improved (90%+)

### Code Review

- [x] Self-reviewed changes
- [x] No unintended changes included
- [x] Only bug fix changes (no scope creep)
- [x] Code follows project standards
- [x] Proper error handling added

### Documentation

- [x] Inline comments explain fix
- [x] Docstrings updated (if needed)
- [x] Commit message complete
- [x] This bug fix report created

### Lead Developer Approval

- [x] Tested by lead developer
- [x] Scenarios verified working
- [x] No regressions observed
- [x] Approved for merge

---

## Impact Assessment

### Performance Impact
[Any performance implications of the fix]
- Latency: [No change / Improved / Degraded by X%]
- Memory: [No change / Improved / Degraded by X%]
- CPU: [No change / Improved / Degraded by X%]

### Breaking Changes
[Any breaking changes introduced]
- API Changes: [Yes/No - describe]
- Configuration Changes: [Yes/No - describe]
- Data Migration Needed: [Yes/No - describe]

### Side Effects
[Any other effects of the fix]
- [Side effect 1]
- [Side effect 2]

---

## Prevention

### How to Prevent Similar Bugs

**Immediate Actions:**
- [Action to prevent this specific bug]

**Long-term Improvements:**
- [Process improvement]
- [Tool addition]
- [Training need]

### Monitoring

**Added Monitoring:**
- [Metric or log added to detect recurrence]
- [Alert configured for similar errors]

**Recommended Monitoring:**
- [Additional monitoring to consider]

---

## Git Information

### Commit

**Branch:** `fix/[bug-description]`

**Commit Message:**
```
fix: [brief description]

Root Cause:
[Explanation]

Fix Applied:
[Changes made]

Impact:
[What this fixes]

Tests:
[Test coverage]

Fixes #[issue-number]

-Agent Generated Commit Message
```

**Commit SHA:** [commit-hash] (filled after commit)

### Pull Request

**PR #:** [number] (filled after PR creation)
**Status:** [Open / Merged / Closed]
**Reviewers:** [list]

---

## Related Issues

- Fixes #[issue-number]
- Related to #[related-issue-number]
- Caused by #[causative-issue-number] (if applicable)

---

## Lessons Learned

### What Went Well
- [Positive aspect of the fix process]

### What Could Be Improved
- [Area for improvement in process or detection]

### Knowledge Shared
- [What the team learned from this bug]

---

## Appendix

### Relevant Logs

```
[Paste relevant log entries showing the bug and the fix]
```

### Screenshots/Diagrams

[Describe or attach visual aids if helpful]

### References

- [Link to related documentation]
- [Link to similar past issues]
- [Link to external resources used]
