# General Anti-Patterns Catalog

This reference covers language-agnostic anti-patterns that appear across all codebases.

## Code Smells

### God Class / Monster Class

**What:** A class that handles too many responsibilities, typically 500+ lines with numerous methods.

**Signs:**
- Class has 10+ methods
- Class has 15+ attributes
- Methods don't relate to each other
- Class name is vague (Manager, Handler, Processor, Utils)

**Fix:** Split into smaller, focused classes following Single Responsibility Principle.

```python
# Bad: God class
class UserManager:
    def create_user(self): ...
    def send_email(self): ...
    def process_payment(self): ...
    def generate_report(self): ...
    def validate_address(self): ...

# Good: Separated concerns
class UserService: ...
class EmailService: ...
class PaymentService: ...
class ReportGenerator: ...
class AddressValidator: ...
```

### Long Method

**What:** Methods exceeding 50 lines that do too much.

**Signs:**
- Multiple levels of abstraction
- Many local variables
- Multiple exit points
- Comments explaining sections

**Fix:** Extract methods, use meaningful names.

### Deep Nesting

**What:** Code with more than 3-4 levels of indentation.

**Signs:**
- Arrow-shaped code
- Difficult to follow logic
- Many conditional branches

**Fix:** Use early returns, extract methods, use guard clauses.

```python
# Bad: Deep nesting
def process(data):
    if data:
        if data.is_valid:
            if data.type == "A":
                if data.status == "active":
                    return handle(data)
    return None

# Good: Early returns
def process(data):
    if not data:
        return None
    if not data.is_valid:
        return None
    if data.type != "A":
        return None
    if data.status != "active":
        return None
    return handle(data)
```

### Magic Numbers

**What:** Unexplained numeric literals in code.

**Signs:**
- Numbers without context
- Same number repeated in multiple places
- Hard to understand what the number means

**Fix:** Use named constants.

```python
# Bad
if retry_count > 3:
    time.sleep(30)

# Good
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30

if retry_count > MAX_RETRIES:
    time.sleep(RETRY_DELAY_SECONDS)
```

### Dead Code

**What:** Code that is never executed.

**Signs:**
- Unreachable code after return/raise
- Unused functions/methods
- Commented-out code
- Unused imports

**Fix:** Delete it. Version control preserves history.

### Copy-Paste Programming

**What:** Duplicated code with minor variations.

**Signs:**
- Similar code blocks
- Same bug fixed in multiple places
- Parallel changes required

**Fix:** Extract common code into functions/classes.

## Coupling Anti-Patterns

### Feature Envy

**What:** A method that uses another object's data more than its own.

**Signs:**
- Method accesses many attributes of another class
- Logic would fit better in the other class

**Fix:** Move the method to the class whose data it uses.

```python
# Bad: Feature envy
class Order:
    def calculate_shipping(self, customer):
        if customer.address.country == "US":
            if customer.address.state == "CA":
                return self.weight * 0.05
            return self.weight * 0.08
        return self.weight * 0.15

# Good: Move to where data lives
class Address:
    def get_shipping_rate(self):
        if self.country == "US":
            return 0.05 if self.state == "CA" else 0.08
        return 0.15
```

### Inappropriate Intimacy

**What:** Classes that know too much about each other's internals.

**Signs:**
- Accessing private/protected members
- Bidirectional associations
- Excessive method calls between classes

**Fix:** Define clear interfaces, reduce dependencies.

### Message Chains

**What:** Long chains of method calls: `a.b().c().d().method()`

**Signs:**
- Violates Law of Demeter
- Fragile to changes
- Hidden dependencies

**Fix:** Introduce intermediate methods, reduce chain length.

```python
# Bad
customer.get_address().get_city().get_postal_code().format()

# Good
customer.get_formatted_postal_code()
```

### Global Variables

**What:** Mutable state accessible from anywhere.

**Signs:**
- Variables defined at module level
- Shared state between functions
- Difficult to test in isolation

**Fix:** Use dependency injection, class instances, or immutable configuration.

## Architectural Anti-Patterns

### Golden Hammer

**What:** Using a familiar tool/pattern for everything, even where it doesn't fit.

**Signs:**
- Same pattern used everywhere
- Overengineered simple solutions
- "We always do it this way"

**Fix:** Choose patterns based on problem requirements.

### Boat Anchor

**What:** Keeping code "just in case" it might be needed.

**Signs:**
- Commented-out code
- Unused classes/functions
- "Legacy" modules no one uses

**Fix:** Delete it. Version control has your back.

### Lava Flow

**What:** Dead code that's too risky to remove because no one understands it.

**Signs:**
- Code with no tests
- No documentation
- "Don't touch this"

**Fix:** Write characterization tests, then refactor or remove.

### Spaghetti Code

**What:** Code with tangled, unclear control flow.

**Signs:**
- Goto-like jumps
- Unclear execution path
- Difficult to debug

**Fix:** Restructure with clear functions and control flow.

## Detection Tools

| Anti-Pattern | Python Tool | JavaScript Tool |
|--------------|-------------|-----------------|
| God Class | radon, pylint | eslint complexity |
| Dead Code | vulture | ts-prune |
| Duplication | pylint | jscpd |
| Complexity | radon cc | eslint complexity |
| All | SonarQube | SonarQube |

## References

- [How to Detect and Prevent Anti-Patterns](https://digma.ai/how-to-detect-and-prevent-anti-patterns/)
- [Types of Anti Patterns to Avoid](https://www.geeksforgeeks.org/blogs/types-of-anti-patterns-to-avoid-in-software-development/)
- [Anti-Patterns - Code Quality Docs](https://docs.embold.io/anti-patterns/)
- [Wikipedia: List of software anti-patterns](https://en.wikipedia.org/wiki/List_of_software_anti-patterns)
