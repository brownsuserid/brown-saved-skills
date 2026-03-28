# Technical Debt Management

This document provides guidance on identifying, prioritizing, and systematically addressing technical debt.

## What is Technical Debt?

**Technical debt:** The implied cost of future reworking required when choosing an easy (but limited) solution now instead of a better approach that would take longer.

**Research finding:** 40% of developers spend 2-5 working days per month on debugging, refactoring, and maintenance caused by technical debt.

---

## Types of Technical Debt

### 1. Deliberate Debt (Tactical)

**Intentional shortcuts to meet deadlines:**
- "We'll ship with this quick fix and refactor later"
- "This isn't scalable, but it works for MVP"

**Managed well:**
- Document the debt
- Create tickets to address it
- Plan time to pay it down

**Example:**
```python
# TODO: This is a temporary solution for MVP
# Replace with proper queue-based processing after launch
# See ticket: TECH-123
def process_orders_sync():
    for order in get_pending_orders():
        process_order(order)  # Blocking, doesn't scale
```

### 2. Accidental Debt

**Emerges from lack of knowledge or changing requirements:**
- Design that seemed good but doesn't fit new needs
- Technology choice that's now outdated
- Pattern that doesn't scale

**Example:**
```python
# Written when we had 100 users, now we have 100,000
def get_all_users():
    return User.query.all()  # Loads everything into memory
```

### 3. Bit Rot

**Code deteriorates over time:**
- Dependencies become outdated
- Patterns become obsolete
- Understanding erodes as team changes

**Example:**
```python
# Uses deprecated library (Python 2.7 era)
import urllib2  # Deprecated, should use requests
```

### 4. AI-Generated Debt (NEW IN 2025)

**From research:** "AI-generated snippets often encourage copy-paste practices instead of thoughtful refactoring, creating bloated, fragile systems."

**Characteristics:**
- High duplication (same pattern repeated with minor variations)
- Missing abstractions
- Copy-paste modifications
- Inconsistent error handling

**Example:**
```python
# AI generated three similar functions instead of one parameterized function
def get_active_users():
    return User.query.filter_by(status="active").all()

def get_inactive_users():
    return User.query.filter_by(status="inactive").all()

def get_pending_users():
    return User.query.filter_by(status="pending").all()

# Should be:
def get_users_by_status(status: str) -> List[User]:
    return User.query.filter_by(status=status).all()
```

---

## Identifying Technical Debt

### Automated Detection

**Use tools to identify issues:**

**1. Code complexity (radon):**
```bash
pip install radon
radon cc app/ -s -a  # Cyclomatic complexity
```

**Output shows functions with high complexity:**
```
F 45:0 process_order - D (23)  # Complexity 23 = HIGH DEBT
```

**2. Code duplication (pylint):**
```bash
pylint --disable=all --enable=duplicate-code app/
```

**3. Dependency analysis:**
```bash
# Find unused dependencies
pip-autoremove --list

# Check for outdated packages
pip list --outdated
```

**4. Dead code detection:**
```bash
# Use vulture to find unused code
pip install vulture
vulture app/
```

### Manual Code Review

**Warning signs of technical debt:**

**❌ Copy-paste programming:**
```python
# Same logic repeated in 5 different places
def calculate_discount_A():
    return price * 0.9

def calculate_discount_B():
    return price * 0.85
```

**❌ Shotgun surgery:**
- One feature change requires editing many files
- Indicates poor cohesion

**❌ Fragile code:**
- Changes in one place break things in another
- Indicates tight coupling

**❌ Difficult onboarding:**
- New developers struggle to understand code
- Indicates poor documentation or bad structure

**❌ Slow feature velocity:**
- Simple features take long time
- Indicates accumulated debt

---

## Measuring Technical Debt

### Code Quality Metrics

**1. Cyclomatic Complexity**
- Measures number of paths through code
- **Target:** < 10 per function
- **Action:** > 15 needs refactoring

**2. Code Duplication**
- Percentage of duplicated code
- **Target:** < 5%
- **Action:** > 10% needs consolidation

**3. Test Coverage**
- Percentage of code covered by tests
- **Target:** > 90%
- **Action:** < 80% increases risk

**4. Dependency Freshness**
- Age of dependencies
- **Target:** < 6 months old
- **Action:** > 1 year needs update

### Time-Based Metrics

**1. Time to implement features**
- Track: Time for similar features over time
- **Trend:** Increasing time = accumulating debt

**2. Bug fix time**
- Track: Time to fix bugs
- **Trend:** Increasing time = code getting harder to maintain

**3. Time spent on maintenance**
- Track: % of sprint on bugs vs features
- **Trend:** Increasing % = debt growing

---

## Prioritizing Technical Debt

Not all debt is equal. Prioritize based on **impact** and **pain**.

### Priority Matrix

**High Priority (Address Soon):**
- High impact on development velocity
- Frequently touched code
- Causes bugs regularly
- Blocks new features

**Medium Priority (Plan to Address):**
- Moderate impact
- Occasionally touched
- Some bugs
- Makes features harder

**Low Priority (Accept or Postpone):**
- Low impact
- Rarely touched
- No bugs
- Doesn't block work

### Prioritization Criteria

**1. Frequency of Change**
```bash
# Find most-changed files (highest priority to refactor)
git log --format=format: --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -20
```

Files changed often + high debt = **TOP PRIORITY**

**2. Bug Density**
```bash
# Find files with most bug fixes
git log --all --oneline --grep="fix\|bug" --name-only | grep "\.py$" | sort | uniq -c | sort -rn
```

**3. Business Value**
- Payment processing code > Internal admin tool
- User-facing features > Background jobs
- Security-related > Nice-to-have

**4. Refactoring Cost**
- Small, isolated module (low cost)
- Core system with many dependencies (high cost)

### Decision Framework

```
Should I refactor this NOW?

1. Is it blocking new features? → YES = High Priority
2. Is it causing bugs regularly? → YES = High Priority
3. Do I need to change it for current work? → YES = High Priority
4. Is it painful but not urgent? → YES = Medium Priority
5. Does it work fine despite being ugly? → YES = Low Priority
```

---

## Addressing Technical Debt

### Strategy 1: Boy Scout Rule

**"Leave code better than you found it."**

**When touching code for feature/bug:**
1. Do the feature/bug work
2. Clean up surrounding code slightly
3. Don't do massive refactoring (scope creep)

**Example:**
```python
# Before: Working on add_item, notice bad naming
def add_item(self, x):  # Bad name
    self.items.append(x)
    self.cnt += 1  # Bad name

# After: Fix names while there
def add_item(self, item):  # Better name
    self.items.append(item)
    self.item_count += 1  # Better name
```

**Benefits:**
- Continuous, incremental improvement
- No dedicated "debt sprint" needed
- Code naturally improves over time

---

### Strategy 2: Dedicated Refactoring Time

**Allocate % of sprint to debt:**
- **20% rule:** 1 day per week on technical debt
- **Refactoring Friday:** Last day of week for cleanup
- **Every 3rd sprint:** Full sprint on debt reduction

**When to use:**
- Debt is significant
- Team velocity slowing
- Major refactoring needed

---

### Strategy 3: Strangler Fig Pattern

**Gradually replace old code:**

**Example: Replacing legacy payment system**

**Phase 1: Create new system alongside old**
```python
# Old system still used
legacy_payment_processor = LegacyPaymentProcessor()

# New system ready
new_payment_processor = NewPaymentProcessor()
```

**Phase 2: Route some traffic to new**
```python
def process_payment(order):
    if order.user.is_beta_tester:
        return new_payment_processor.process(order)
    else:
        return legacy_payment_processor.process(order)
```

**Phase 3: Route all traffic to new**
```python
def process_payment(order):
    return new_payment_processor.process(order)
```

**Phase 4: Remove old system**
```python
# legacy_payment_processor deleted
```

**Benefits:**
- Low risk (can rollback at any phase)
- Incremental (no big-bang rewrite)
- Validated in production gradually

---

### Strategy 4: Stop the Bleeding

**Before fixing old debt, prevent new debt:**

**1. Enforce standards in PR reviews**
- No duplicate code
- Maximum complexity limits
- Required test coverage

**2. Add automated checks**
```yaml
# .github/workflows/quality.yml
- name: Check complexity
  run: radon cc app/ --min D  # Fail if complexity too high

- name: Check duplication
  run: pylint --duplicate-code app/

- name: Check coverage
  run: pytest --cov=app --cov-fail-under=90
```

**3. Document patterns**
- "This is how we do X"
- Reduces ad-hoc solutions

---

## Tracking Technical Debt

### Create Debt Tickets

**Format:**
```markdown
Title: [TECH DEBT] High complexity in order processing

**Description:**
The `process_order` function has cyclomatic complexity of 23 (target: <10).
This makes it difficult to maintain and test.

**Impact:**
- Slows down feature development in order module
- Source of 3 bugs in last quarter
- Difficult for new developers to understand

**Location:**
- File: app/services/order_processor.py
- Function: process_order (lines 45-180)

**Proposed Solution:**
Extract methods:
1. validate_order()
2. calculate_totals()
3. process_payment()
4. send_confirmation()

**Estimated Effort:** 4 hours

**Priority:** High (touched frequently, causes bugs)
```

### Track in Project Management

**Label tickets:**
- `tech-debt`
- `refactoring`
- `code-quality`

**Track metrics:**
- Number of debt tickets created
- Number resolved
- Age of oldest debt ticket
- Time spent on debt vs features

### Regular Debt Review

**Monthly review:**
1. What new debt was created?
2. What debt was resolved?
3. What's blocking us most?
4. What's our debt trend?

**Adjust strategy based on trend:**
- Debt growing → Increase refactoring time
- Debt stable → Current approach working
- Debt shrinking → Great! Maintain pace

---

## Preventing Technical Debt

### During Development

**1. Think before accepting AI code**
- Does this duplicate existing logic?
- Should this be extracted to utility?
- Is this the right abstraction?

**2. Write tests first (TDD)**
- Forces good design
- Makes refactoring safe

**3. Review code before committing**
- Does this follow standards?
- Is this maintainable?
- Will I understand this in 6 months?

### During Code Review

**Flag debt immediately:**
```markdown
⚠️ **Technical Debt: Duplication**

This logic is similar to `calculate_discount` in pricing.py:42.
Consider extracting shared function.

If we accept this now, create ticket to consolidate later.
```

**Options:**
1. Fix it now (if small)
2. Create debt ticket for later
3. Reject PR until fixed (if significant)

### During Planning

**Include refactoring in estimates:**
```
Story: Add discount codes to checkout

Estimate: 8 points
- Feature implementation: 5 points
- Refactor pricing module: 2 points
- Tests: 1 point
```

**Benefits:**
- Refactoring is explicit
- Debt doesn't accumulate
- Code quality maintained

---

## Communicating Technical Debt

### To Management

**Frame in business terms:**

**❌ Don't say:**
"We have high cyclomatic complexity in the order processor."

**✓ Do say:**
"Our order processing code is becoming difficult to maintain. This is slowing down new feature development by ~20% and causing bugs. We recommend allocating 2 days to refactor it, which will improve our velocity going forward."

**Show impact:**
- Development velocity decreasing
- Bug rate increasing
- Feature estimates growing
- Developer frustration growing

### To Team

**Keep visible:**
- Dashboard showing debt metrics
- Regular debt discussions in retros
- Celebrate debt reduction

**Foster culture:**
- Refactoring is valuable work (not "wasted time")
- Boy Scout Rule is default
- Quality matters

---

## Summary

**Technical debt is inevitable:**
- All code accumulates some debt
- Goal: Manage it, don't eliminate it

**Key strategies:**
- **Prevent:** Stop creating new debt (reviews, standards)
- **Measure:** Track complexity, duplication, coverage
- **Prioritize:** Focus on high-impact debt
- **Address:** Boy Scout Rule + dedicated time
- **Track:** Document and monitor debt

**Modern challenge:**
- AI generates code faster than ever
- Risk: Accumulating AI-generated duplication
- Solution: Review and consolidate AI code immediately

**Remember:**
**Paying down debt increases velocity.**
**Ignoring debt compounds interest.**
