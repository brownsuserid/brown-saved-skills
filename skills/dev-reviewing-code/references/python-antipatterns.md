# Python Anti-Patterns Catalog

This reference covers Python-specific anti-patterns and bad practices.

## Correctness Anti-Patterns

### Mutable Default Arguments

**What:** Using mutable objects (lists, dicts) as default arguments.

**Why Bad:** Default arguments are evaluated once at function definition, not each call.

```python
# Bad: Mutable default
def add_item(item, items=[]):
    items.append(item)
    return items

add_item(1)  # [1]
add_item(2)  # [1, 2] - Unexpected!

# Good: Use None
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### Bare Except Clauses

**What:** Using `except:` without specifying exception type.

**Why Bad:** Catches everything including KeyboardInterrupt, SystemExit.

```python
# Bad
try:
    risky_operation()
except:
    pass

# Good: Specific exceptions
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except ConnectionError:
    retry_operation()
```

### Using `type()` for Type Checking

**What:** Using `type(x) == SomeType` instead of `isinstance()`.

**Why Bad:** Doesn't handle inheritance properly.

```python
# Bad
if type(obj) == dict:
    process_dict(obj)

# Good: Handles subclasses
if isinstance(obj, dict):
    process_dict(obj)

# Better: Use ABC for duck typing
from collections.abc import Mapping
if isinstance(obj, Mapping):
    process_mapping(obj)
```

### Comparing with `==` for None/True/False

**What:** Using `==` instead of `is` for singletons.

```python
# Bad
if x == None:
    ...
if flag == True:
    ...

# Good
if x is None:
    ...
if flag is True:  # or just: if flag:
    ...
```

## Resource Management Anti-Patterns

### Not Using Context Managers for Files

**What:** Opening files without `with` statement.

**Why Bad:** Files may not close on exceptions, causing resource leaks.

```python
# Bad
f = open("file.txt")
data = f.read()
f.close()  # May not reach if exception

# Good
with open("file.txt") as f:
    data = f.read()
# File automatically closed
```

### Not Closing Database Connections

**What:** Opening connections without ensuring closure.

```python
# Bad
conn = psycopg2.connect(...)
cursor = conn.cursor()
cursor.execute(query)
# Connection leak if exception

# Good
with psycopg2.connect(...) as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
```

## Import Anti-Patterns

### Wildcard Imports

**What:** Using `from module import *`.

**Why Bad:**
- Pollutes namespace
- Unclear what's imported
- Breaks static analysis tools
- Can cause name collisions

```python
# Bad
from os.path import *
from utils import *

# Good: Explicit imports
from os.path import join, dirname
from utils import helper_function
```

### Circular Imports

**What:** Module A imports B, and B imports A.

**Fix:**
- Restructure modules
- Use late imports (inside functions)
- Create a third module for shared code

```python
# If unavoidable, use late import
def some_function():
    from other_module import needed_function
    return needed_function()
```

## String Anti-Patterns

### String Concatenation in Loops

**What:** Building strings with `+=` in loops.

**Why Bad:** Creates new string objects each iteration (O(n²)).

```python
# Bad: O(n²) complexity
result = ""
for item in items:
    result += str(item) + ", "

# Good: O(n) complexity
result = ", ".join(str(item) for item in items)
```

### Using `+` for String Formatting

**What:** Concatenating strings with variables.

```python
# Bad
message = "Hello, " + name + "! You have " + str(count) + " items."

# Good: f-strings (Python 3.6+)
message = f"Hello, {name}! You have {count} items."
```

## Function Anti-Patterns

### Returning Multiple Types

**What:** Function returns different types based on conditions.

**Why Bad:** Callers must handle multiple types, type hints become complex.

```python
# Bad
def get_user(user_id):
    user = db.find(user_id)
    if user:
        return user
    return None  # or return False, or return ""

# Good: Consistent return type
def get_user(user_id) -> User | None:
    return db.find(user_id)

# Better: Raise exception for errors
def get_user(user_id) -> User:
    user = db.find(user_id)
    if not user:
        raise UserNotFoundError(user_id)
    return user
```

### Too Many Arguments

**What:** Functions with more than 5-6 parameters.

**Fix:** Use dataclasses, TypedDict, or parameter objects.

```python
# Bad
def create_user(name, email, age, address, city, state, zip_code, country):
    ...

# Good: Use dataclass
@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str

@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int
    address: Address

def create_user(request: CreateUserRequest):
    ...
```

### Using `assert` for Validation

**What:** Using `assert` to validate user input or API data.

**Why Bad:** Assertions are removed when running with `-O` flag.

```python
# Bad
def process_payment(amount):
    assert amount > 0, "Amount must be positive"
    ...

# Good: Raise proper exceptions
def process_payment(amount):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    ...
```

## Class Anti-Patterns

### Not Using `__slots__`

**What:** Large classes without `__slots__` when memory matters.

**When to use:** When creating many instances of a class.

```python
# Memory inefficient for many instances
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# Memory efficient
class Point:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y
```

### Unnecessary Classes

**What:** Classes that should just be functions.

```python
# Bad: Class with single method
class StringCleaner:
    def clean(self, text):
        return text.strip().lower()

cleaner = StringCleaner()
result = cleaner.clean(input)

# Good: Just a function
def clean_string(text):
    return text.strip().lower()

result = clean_string(input)
```

## Detection Tools

| Tool | Purpose | Command |
|------|---------|---------|
| pylint | Comprehensive linting | `pylint .` |
| flake8 | Style + errors | `flake8 .` |
| wemake-python-styleguide | Strict anti-patterns | `flake8 --select=WPS` |
| vulture | Dead code | `vulture .` |
| radon | Complexity | `radon cc . -a` |
| mypy | Type errors | `mypy .` |
| bandit | Security issues | `bandit -r .` |

## References

- [The Little Book of Python Anti-Patterns](https://docs.quantifiedcode.com/python-anti-patterns/)
- [DeepSource Python Anti-Patterns](https://deepsource.com/blog/8-new-python-antipatterns)
- [QuantifiedCode GitHub](https://github.com/quantifiedcode/python-anti-patterns)
