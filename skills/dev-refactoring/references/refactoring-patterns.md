# Refactoring Patterns Reference

This document provides patterns, techniques, and best practices for refactoring code to improve quality while preserving functionality.

## Overview

**Refactoring:** Improving code structure without changing external behavior.

**Why refactor:**
- Reduce technical debt (40% of developers spend 2-5 days/month on debt)
- Improve maintainability
- Prevent AI-generated code from creating bloated systems
- Prepare for new features
- Make code easier to understand

**When to refactor:**
- Before adding new features (clean up first)
- When code is difficult to understand
- When duplication is discovered
- When patterns emerge
- During code review

**When NOT to refactor:**
- Just to use new technology ("rewrite for the sake of rewriting")
- Without tests (refactor with safety net)
- Mixed with feature work (keep separate)
- On code that will be deleted soon

---

## Refactoring Strategy

### Incremental, Not Revolutionary

**❌ Don't:** Rewrite entire modules or systems
**✓ Do:** Make small, incremental improvements

**Why:** Large refactoring projects often fail, while incremental changes succeed.

**Research shows:** Teams trained in AI-assisted refactoring achieve **3x faster modernization** through phased strategies.

### The Strangler Fig Pattern

Incrementally replace old code with new implementation:

1. **Identify:** Portion to refactor
2. **Create:** New implementation alongside old
3. **Redirect:** Route new calls to new implementation
4. **Verify:** Old implementation no longer used
5. **Remove:** Delete old code

**Example:**
```python
# Phase 1: Old implementation
def calculate_price(item):
    # Legacy pricing logic
    ...

# Phase 2: Create new implementation
def calculate_price_v2(item):
    # New pricing logic
    ...

# Phase 3: Redirect callers
def calculate_price(item):
    # Temporary: Route to new implementation
    return calculate_price_v2(item)

# Phase 4: After verification, remove old function
# Only calculate_price_v2 remains
```

---

## Common Code Smells

### 1. Duplicate Code

**Smell:** Same or similar code in multiple places

**Impact:**
- Changes must be made in multiple places
- Easy to miss one location
- Maintenance burden increases

**Example:**
```python
# ❌ BAD: Duplicate discount logic
def calculate_discount_premium(price):
    """Calculate discount for premium members."""
    return price * 0.8

def calculate_discount_standard(price):
    """Calculate discount for standard members."""
    return price * 0.9

def calculate_discount_vip(price):
    """Calculate discount for VIP members."""
    return price * 0.7
```

**Refactoring:** Extract common pattern

```python
# ✓ GOOD: Single function with parameter
DISCOUNT_RATES = {
    "premium": 0.2,
    "standard": 0.1,
    "vip": 0.3
}

def calculate_discount(price: float, membership_level: str) -> float:
    """Calculate discount based on membership level.

    Args:
        price: Original price
        membership_level: Member tier (premium, standard, vip)

    Returns:
        Discounted price
    """
    discount_rate = DISCOUNT_RATES.get(membership_level, 0)
    return price * (1 - discount_rate)
```

---

### 2. Long Functions

**Smell:** Functions > 50 lines or doing multiple things

**Impact:**
- Hard to understand
- Hard to test
- Hard to reuse
- Violates Single Responsibility Principle

**Example:**
```python
# ❌ BAD: Long function doing everything
def process_order(order_data):
    """Process order from start to finish."""
    # Validate order (20 lines)
    if not order_data.get("user_id"):
        raise ValueError("Missing user_id")
    if not order_data.get("items"):
        raise ValueError("Missing items")
    # ... more validation

    # Calculate totals (15 lines)
    subtotal = 0
    for item in order_data["items"]:
        subtotal += item["price"] * item["quantity"]
    tax = subtotal * 0.08
    total = subtotal + tax
    # ... more calculation

    # Process payment (25 lines)
    payment_method = order_data["payment_method"]
    if payment_method == "credit_card":
        # ... credit card logic
    elif payment_method == "paypal":
        # ... paypal logic
    # ... more payment logic

    # Send confirmation (10 lines)
    email = get_user_email(order_data["user_id"])
    # ... email logic

    return order_id
```

**Refactoring:** Extract methods

```python
# ✓ GOOD: Single responsibility per function
def process_order(order_data: dict) -> str:
    """Process order from start to finish.

    Args:
        order_data: Order information

    Returns:
        Order ID
    """
    validate_order(order_data)
    totals = calculate_order_totals(order_data)
    payment_result = process_payment(order_data, totals)
    send_order_confirmation(order_data, payment_result)
    return payment_result.order_id

def validate_order(order_data: dict) -> None:
    """Validate order data."""
    if not order_data.get("user_id"):
        raise ValueError("Missing user_id")
    if not order_data.get("items"):
        raise ValueError("Missing items")
    # ... validation logic

def calculate_order_totals(order_data: dict) -> OrderTotals:
    """Calculate order subtotal, tax, and total."""
    subtotal = sum(
        item["price"] * item["quantity"]
        for item in order_data["items"]
    )
    tax = subtotal * TAX_RATE
    return OrderTotals(subtotal=subtotal, tax=tax, total=subtotal + tax)

def process_payment(order_data: dict, totals: OrderTotals) -> PaymentResult:
    """Process payment for order."""
    # Payment logic

def send_order_confirmation(order_data: dict, payment_result: PaymentResult) -> None:
    """Send order confirmation email."""
    # Email logic
```

---

### 3. Complex Conditionals

**Smell:** Nested if/else, multiple conditions, hard to understand logic

**Impact:**
- Difficult to read
- Easy to miss branches
- Hard to test all paths
- Error-prone

**Example:**
```python
# ❌ BAD: Nested conditionals
def can_access_resource(user, resource):
    if user:
        if user.is_authenticated:
            if resource:
                if resource.is_public:
                    return True
                elif user.is_admin:
                    return True
                elif resource.owner_id == user.id:
                    return True
    return False
```

**Refactoring: Early returns**

```python
# ✓ GOOD: Early returns, flat structure
def can_access_resource(user: User, resource: Resource) -> bool:
    """Check if user can access resource.

    Args:
        user: User requesting access
        resource: Resource to access

    Returns:
        True if user has access, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    if not resource:
        return False

    # Public resources accessible to all authenticated users
    if resource.is_public:
        return True

    # Admins have access to everything
    if user.is_admin:
        return True

    # Owners have access to their resources
    if resource.owner_id == user.id:
        return True

    return False
```

**Refactoring: Extract conditions to methods**

```python
# ✓ BETTER: Extract complex conditions
def can_access_resource(user: User, resource: Resource) -> bool:
    """Check if user can access resource."""
    if not is_valid_user(user):
        return False

    if not resource:
        return False

    return (
        resource.is_public or
        is_admin(user) or
        is_resource_owner(user, resource)
    )

def is_valid_user(user: User) -> bool:
    """Check if user is valid and authenticated."""
    return user is not None and user.is_authenticated

def is_admin(user: User) -> bool:
    """Check if user is an administrator."""
    return user.is_admin

def is_resource_owner(user: User, resource: Resource) -> bool:
    """Check if user owns the resource."""
    return resource.owner_id == user.id
```

---

### 4. Large Classes (God Objects)

**Smell:** Classes with too many responsibilities

**Impact:**
- Difficult to understand
- Difficult to test
- Violates Single Responsibility
- High coupling

**Example:**
```python
# ❌ BAD: God object doing everything
class User:
    """User class handling everything user-related."""

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def authenticate(self, password):
        """Authenticate user."""
        # Authentication logic

    def send_email(self, subject, body):
        """Send email to user."""
        # Email sending logic

    def process_payment(self, amount):
        """Process payment for user."""
        # Payment processing logic

    def generate_report(self):
        """Generate user activity report."""
        # Report generation logic

    def update_preferences(self, preferences):
        """Update user preferences."""
        # Preference logic
```

**Refactoring:** Extract responsibilities into separate classes

```python
# ✓ GOOD: Single Responsibility Principle
class User:
    """User data model."""

    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email


class AuthenticationService:
    """Handle user authentication."""

    def authenticate(self, user: User, password: str) -> bool:
        """Authenticate user with password."""
        # Authentication logic


class EmailService:
    """Handle email sending."""

    def send_email(self, to: str, subject: str, body: str) -> None:
        """Send email to recipient."""
        # Email sending logic


class PaymentService:
    """Handle payment processing."""

    def process_payment(self, user: User, amount: float) -> PaymentResult:
        """Process payment for user."""
        # Payment processing logic


class ReportGenerator:
    """Generate user reports."""

    def generate_user_report(self, user: User) -> Report:
        """Generate activity report for user."""
        # Report generation logic
```

---

### 5. Feature Envy

**Smell:** Method in one class uses data from another class more than its own

**Impact:**
- Wrong responsibility placement
- Tight coupling
- Difficult to maintain

**Example:**
```python
# ❌ BAD: Feature envy
class Order:
    def __init__(self, items):
        self.items = items

class OrderProcessor:
    def calculate_total(self, order):
        """Calculate order total."""
        # Uses order's data extensively
        subtotal = sum(item.price * item.quantity for item in order.items)
        tax = subtotal * 0.08
        shipping = self._calculate_shipping(order.items)
        return subtotal + tax + shipping

    def _calculate_shipping(self, items):
        """Calculate shipping cost."""
        total_weight = sum(item.weight * item.quantity for item in items)
        return total_weight * 0.5
```

**Refactoring:** Move method to appropriate class

```python
# ✓ GOOD: Responsibility in correct place
class Order:
    """Order with items and calculations."""

    def __init__(self, items: List[Item]):
        self.items = items

    def calculate_subtotal(self) -> float:
        """Calculate order subtotal."""
        return sum(item.price * item.quantity for item in self.items)

    def calculate_tax(self) -> float:
        """Calculate order tax."""
        return self.calculate_subtotal() * TAX_RATE

    def calculate_shipping(self) -> float:
        """Calculate shipping cost based on weight."""
        total_weight = sum(item.weight * item.quantity for item in self.items)
        return total_weight * SHIPPING_RATE_PER_LB

    def calculate_total(self) -> float:
        """Calculate order total with tax and shipping."""
        return (
            self.calculate_subtotal() +
            self.calculate_tax() +
            self.calculate_shipping()
        )


class OrderProcessor:
    """Process orders."""

    def process_order(self, order: Order) -> PaymentResult:
        """Process order payment."""
        total = order.calculate_total()  # Use Order's method
        return self.payment_service.charge(total)
```

---

### 6. Primitive Obsession

**Smell:** Using primitives (str, int) instead of small objects

**Impact:**
- Logic scattered across codebase
- Validation duplicated
- Difficult to enforce constraints

**Example:**
```python
# ❌ BAD: Primitive obsession
def send_email(email_address: str, subject: str, body: str):
    # Email validation logic scattered
    if "@" not in email_address:
        raise ValueError("Invalid email")
    if len(email_address) < 5:
        raise ValueError("Email too short")
    # ... send email


def create_user(email: str):
    # Same validation duplicated
    if "@" not in email:
        raise ValueError("Invalid email")
    # ... create user
```

**Refactoring:** Create value object

```python
# ✓ GOOD: Value object encapsulates validation
class EmailAddress:
    """Email address value object."""

    def __init__(self, address: str):
        self._validate(address)
        self._address = address

    @staticmethod
    def _validate(address: str) -> None:
        """Validate email address format."""
        if not address:
            raise ValueError("Email address cannot be empty")
        if "@" not in address:
            raise ValueError("Invalid email format")
        if len(address) < 5:
            raise ValueError("Email address too short")
        # More validation...

    @property
    def address(self) -> str:
        """Get email address string."""
        return self._address

    def __str__(self) -> str:
        return self._address

    def __eq__(self, other) -> bool:
        if not isinstance(other, EmailAddress):
            return False
        return self._address == other._address


def send_email(email: EmailAddress, subject: str, body: str):
    """Send email (validation already done)."""
    # No validation needed - EmailAddress guarantees validity
    ...


def create_user(email: EmailAddress):
    """Create user (validation already done)."""
    # No validation needed
    ...
```

---

## Refactoring Techniques

### Extract Method

**When:** Function is too long or does multiple things

**Before:**
```python
def generate_report(users):
    # Calculate statistics
    total = len(users)
    active = sum(1 for u in users if u.is_active)
    inactive = total - active

    # Format output
    report = f"Total Users: {total}\n"
    report += f"Active: {active}\n"
    report += f"Inactive: {inactive}\n"

    return report
```

**After:**
```python
def generate_report(users: List[User]) -> str:
    """Generate user statistics report."""
    stats = calculate_user_statistics(users)
    return format_statistics_report(stats)

def calculate_user_statistics(users: List[User]) -> UserStatistics:
    """Calculate user statistics."""
    total = len(users)
    active = sum(1 for u in users if u.is_active)
    return UserStatistics(total=total, active=active, inactive=total - active)

def format_statistics_report(stats: UserStatistics) -> str:
    """Format statistics as text report."""
    return (
        f"Total Users: {stats.total}\n"
        f"Active: {stats.active}\n"
        f"Inactive: {stats.inactive}\n"
    )
```

### Extract Variable

**When:** Complex expression is hard to understand

**Before:**
```python
if (user.age >= 18 and user.has_verified_email and
    user.account_created_days_ago > 30 and not user.is_suspended):
    grant_access()
```

**After:**
```python
is_adult = user.age >= 18
has_verified_email = user.has_verified_email
is_established_account = user.account_created_days_ago > 30
is_in_good_standing = not user.is_suspended

if is_adult and has_verified_email and is_established_account and is_in_good_standing:
    grant_access()
```

### Replace Magic Number with Constant

**When:** Unexplained numbers in code

**Before:**
```python
def calculate_shipping(weight):
    if weight > 50:
        return weight * 0.05
    return weight * 0.08
```

**After:**
```python
HEAVY_PACKAGE_THRESHOLD_LBS = 50
HEAVY_PACKAGE_RATE = 0.05
STANDARD_PACKAGE_RATE = 0.08

def calculate_shipping(weight: float) -> float:
    """Calculate shipping cost based on weight."""
    if weight > HEAVY_PACKAGE_THRESHOLD_LBS:
        return weight * HEAVY_PACKAGE_RATE
    return weight * STANDARD_PACKAGE_RATE
```

### Replace Conditional with Polymorphism

**When:** Type-checking with if/elif chains

**Before:**
```python
def calculate_area(shape):
    if shape.type == "circle":
        return 3.14 * shape.radius ** 2
    elif shape.type == "rectangle":
        return shape.width * shape.height
    elif shape.type == "triangle":
        return 0.5 * shape.base * shape.height
```

**After:**
```python
class Shape(ABC):
    @abstractmethod
    def calculate_area(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def calculate_area(self) -> float:
        return 3.14 * self.radius ** 2

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def calculate_area(self) -> float:
        return self.width * self.height

class Triangle(Shape):
    def __init__(self, base: float, height: float):
        self.base = base
        self.height = height

    def calculate_area(self) -> float:
        return 0.5 * self.base * self.height

# Usage
area = shape.calculate_area()  # Polymorphic call
```

---

## Preventing AI-Generated Technical Debt

**Research finding:** AI-generated snippets often encourage copy-paste practices, creating bloated, fragile systems.

### Strategies

**1. Review AI-generated code for duplication**

After AI generates code:
```bash
# Search for similar patterns
rg "def calculate_discount" --type py
```

If multiple similar functions found, consolidate into single function.

**2. Extract patterns immediately**

Don't accept AI-generated duplication:
```python
# ❌ AI might generate:
def process_user_registration(data):
    # 50 lines of logic

def process_admin_registration(data):
    # 48 lines of same logic with 2 line difference

# ✓ Immediately refactor:
def process_registration(data, user_type):
    # Unified logic with user_type parameter
```

**3. Enforce DRY in code review**

Flag AI-generated duplication in PRs:
```markdown
💡 **Suggestion: Consolidate duplicate logic**

The user and admin registration functions share 95% of code.
Extract common logic into shared function.
```

**4. Use AI to identify refactoring opportunities**

Ask AI to analyze for patterns:
```
"Analyze these functions and identify duplicate code patterns that should be extracted into shared utilities."
```

---

## Refactoring Workflow

### Safe Refactoring Process

**1. Ensure tests exist**
- If no tests, write characterization tests first
- Tests are your safety net

**2. Make one change at a time**
- Extract one method
- Run tests
- Commit
- Extract next method

**3. Run tests after each change**
```bash
pytest tests/
```

**4. Commit frequently**
```bash
git add .
git commit -m "refactor: extract calculate_totals method"
```

**5. Keep refactoring separate from features**
- Refactoring PR: Only restructuring
- Feature PR: Only new functionality

### Refactoring Checklist

Before refactoring:
- [ ] Tests exist and pass
- [ ] Understand current behavior
- [ ] Have clear goal for improvement
- [ ] Create feature branch

During refactoring:
- [ ] Make one change at a time
- [ ] Run tests after each change
- [ ] Commit frequently
- [ ] Preserve external behavior

After refactoring:
- [ ] All tests still pass
- [ ] No new functionality added
- [ ] Code is more maintainable
- [ ] Create PR for review

---

## Summary

**Key principles:**
- Refactor incrementally (not revolutionary rewrites)
- Always have tests as safety net
- One change at a time
- Keep refactoring separate from features
- Focus on improving maintainability
- Prevent AI-generated duplication

**Common smells:**
- Duplicate code → Extract common logic
- Long functions → Extract methods
- Complex conditionals → Early returns or extract conditions
- God objects → Split responsibilities
- Feature envy → Move method
- Primitive obsession → Create value objects

**Refactoring = Continuous improvement, not one-time event**
