# Root Cause Analysis Guide

This guide provides systematic techniques for investigating bugs and identifying their root causes.

## Investigation Methodology

### Step 1: Generate Multiple Hypotheses

Always list **at least 3 plausible causes** before investigating. This prevents tunnel vision and ensures thorough analysis.

#### Common Categories of Bugs

**Code Logic Errors:**
- Off-by-one errors in loops or array indexing
- Incorrect conditional logic (wrong comparison operators)
- Missing edge case handling
- Incorrect algorithm implementation
- Copy-paste errors with unchanged variables

**Data & Type Issues:**
- Null/undefined/None checks missing
- Type mismatches (string vs integer, etc.)
- Data validation failures
- Incorrect data transformations
- Missing data sanitization

**Dependency Problems:**
- Missing imports or incorrect import paths
- Version conflicts between dependencies
- API changes in updated libraries
- Missing or incorrect environment variables
- Circular dependencies

**Configuration Issues:**
- Incorrect configuration values
- Missing configuration files
- Environment-specific settings
- Database connection strings
- API keys or credentials

**Concurrency & Race Conditions:**
- Shared state without proper locking
- Async operations completing in unexpected order
- Database transaction conflicts
- File system race conditions
- Event timing issues

**Resource Management:**
- Memory leaks (objects not garbage collected)
- File handles not closed
- Database connections not released
- API rate limits exceeded
- Disk space exhaustion

### Step 2: Validation Techniques

For each hypothesis, use systematic validation:

#### Using the Read Tool
```
Read the file containing the error:
- Note line numbers for exact error location
- Check surrounding context (20-30 lines before/after)
- Look for variable definitions and their scope
- Trace data flow through the function
```

#### Using the Grep Tool
```
Search for related patterns:
- Function definitions that may be involved
- Variable usage across the codebase
- Similar error patterns from past fixes
- Import statements for dependencies
- Configuration references
```

#### Using the Task (Explore) Tool
```
Explore broader context when:
- Error involves multiple files
- Need to understand system architecture
- Searching for similar patterns across codebase
- Understanding data flow through system
```

### Step 3: Cross-Reference & Validate

#### Execution Path Tracing (Call Stack Navigation)

**Systematic Backward Tracing:**
1. **Start at the error point** - Document where the error manifests
2. **Find immediate cause** - What code is executing when it fails?
3. **Navigate upward** - What called this function? What parameters were passed?
4. **Trace recursively** - Continue asking "what called this?" at each level
5. **Find the origin** - Where did the invalid data/state originate?

**Key Questions at Each Level:**
- What function called this?
- What data was passed in?
- Where did that data come from?
- Was the data valid at entry?
- Did this function validate its inputs?

**Use Stack Traces Effectively:**
- Full stack traces show complete call chains
- Start at the bottom (error point) and work upward
- Pay attention to intermediate functions that passed data through
- Look for functions that transformed or validated (or failed to validate) data

#### Dependency Chain Analysis
- Map all dependencies involved
- Check for version compatibility
- Verify import order (can affect initialization)
- Look for circular dependencies
- Check for side effects in imports

#### Data Flow Analysis
- Trace data from input to error point
- Check all transformations applied
- Verify data types at each step
- Look for unexpected mutations
- Check for data sanitization

### Step 4: Confirm or Rule Out Hypotheses

Document your findings for each hypothesis:

**Hypothesis 1: [Description]**
- **Evidence For:** [What supports this hypothesis]
- **Evidence Against:** [What contradicts this hypothesis]
- **Conclusion:** CONFIRMED / RULED OUT
- **Reasoning:** [Why you reached this conclusion]

**Hypothesis 2: [Description]**
- **Evidence For:** [...]
- **Evidence Against:** [...]
- **Conclusion:** CONFIRMED / RULED OUT
- **Reasoning:** [...]

**Hypothesis 3: [Description]**
- **Evidence For:** [...]
- **Evidence Against:** [...]
- **Conclusion:** CONFIRMED / RULED OUT
- **Reasoning:** [...]

## Common Bug Patterns & How to Find Them

### Pattern: Off-by-One Errors

**Symptoms:**
- IndexError, list index out of range
- Loop executing one too many/few times
- Last/first item in collection not processed

**How to Find:**
- Check loop conditions: `<` vs `<=`, `>` vs `>=`
- Verify array indexing starts at correct position (0 vs 1)
- Check range boundaries: `range(len(arr))` vs `range(len(arr) - 1)`

### Pattern: Null/Undefined Checks Missing

**Symptoms:**
- AttributeError: 'NoneType' object has no attribute
- TypeError: cannot perform operation on None
- Unexpected None values propagating

**How to Find:**
- Search for function calls that can return None
- Check for missing null guards after database queries
- Look for optional parameters without defaults
- Verify error handling for failed operations

### Pattern: Type Mismatches

**Symptoms:**
- TypeError: unsupported operand types
- Comparison failures
- JSON serialization errors
- Database type errors

**How to Find:**
- Check function signatures and type hints
- Verify data coming from external sources (APIs, user input)
- Look for implicit type conversions
- Check for string/int/float confusion

### Pattern: Race Conditions

**Symptoms:**
- Intermittent failures
- Works in debug mode but fails in production
- Results depend on timing
- Concurrent access errors

**How to Find:**
- Look for shared state between async operations
- Check for missing locks/mutexes
- Verify atomic operations
- Look for check-then-act patterns without synchronization

### Pattern: Resource Leaks

**Symptoms:**
- Memory usage grows over time
- "Too many open files" errors
- Database connection pool exhausted
- Performance degradation over time

**How to Find:**
- Check for missing `close()` calls
- Look for exception handling that skips cleanup
- Verify context managers (`with` statements) are used
- Check for circular references preventing garbage collection

## Investigation Checklist

When investigating a bug, systematically check:

- [ ] **Error Message Analysis**
  - What is the exact error message?
  - What file and line number?
  - What is the stack trace?

- [ ] **Context Gathering**
  - When does it occur? (always, intermittent, specific conditions)
  - What input triggers it?
  - What was the expected vs actual behavior?

- [ ] **Recent Changes**
  - What code changed recently?
  - Were dependencies updated?
  - Did configuration change?

- [ ] **Environment**
  - Does it reproduce in all environments?
  - Is it environment-specific configuration?
  - Are there version differences?

- [ ] **Data Analysis**
  - What data is involved?
  - Is the data in expected format/type?
  - Are there edge cases in the data?

- [ ] **Dependencies**
  - Are all dependencies installed?
  - Are versions compatible?
  - Are environment variables set?

## Example Investigation

### Bug Report
```
Error: KeyError: 'user_id' in process_user_data()
Occurs when processing webhook from external API
```

### Hypothesis Generation
1. **Hypothesis:** External API changed response format, no longer includes 'user_id'
2. **Hypothesis:** 'user_id' is conditionally included, missing in some cases
3. **Hypothesis:** Code expects nested structure but data is flat (or vice versa)

### Investigation
```
Hypothesis 1 - API format change:
- Read API documentation (last updated 3 months ago)
- Check webhook payload examples
- Grep for other places handling this webhook
- RULED OUT: Other handlers working fine, docs show user_id required

Hypothesis 2 - Conditional inclusion:
- Read webhook handler code
- Check for conditional logic around user_id
- Review API docs for when user_id might be omitted
- RULED OUT: API docs say user_id is always present

Hypothesis 3 - Nested structure mismatch:
- Read the actual error location (line 42)
- Check webhook payload structure
- Compare with code expectations
- CONFIRMED: Code does data['user_id'] but actual structure is data['user']['id']
```

### Root Cause
The webhook payload has a nested structure `{'user': {'id': 123, ...}}` but the code incorrectly tries to access `data['user_id']` instead of `data['user']['id']`.

## Instrumentation Techniques

When manual tracing proves difficult, add diagnostic logging to understand execution flow.

### Strategic Logging Placement

**Place logs BEFORE dangerous operations, not after failures:**
```python
# ❌ BAD - Too late, won't execute if operation fails
result = dangerous_operation()
logger.debug(f"Operation result: {result}")

# ✓ GOOD - Captures context before potential failure
logger.debug(f"About to execute operation with: {param1}, {param2}")
result = dangerous_operation()
```

### What to Log

**Include relevant context:**
- Current working directory: `os.getcwd()`
- Environment variables: `os.environ.get('KEY')`
- Parameter values and their types
- Execution stack: `new Error().stack` (JavaScript) or `traceback.format_stack()` (Python)
- State of relevant objects before operation

**Example:**
```python
import traceback
import os

def process_data(filepath):
    # Log context before processing
    print(f"DEBUG: Processing {filepath}", file=sys.stderr)
    print(f"DEBUG: CWD: {os.getcwd()}", file=sys.stderr)
    print(f"DEBUG: File exists: {os.path.exists(filepath)}", file=sys.stderr)
    print(f"DEBUG: Call stack:\n{''.join(traceback.format_stack())}", file=sys.stderr)

    # Now do the actual work
    with open(filepath) as f:
        return f.read()
```

### Logging in Tests

**Important:** Use `print()` or `console.error()` in tests, not logger:
- Standard loggers may not show output during test runs
- `stderr` is typically visible in test output
- Helps debug test failures

```python
# In tests - use print to stderr
import sys

def test_something():
    print(f"DEBUG: Test starting with {test_data}", file=sys.stderr)
    result = function_under_test(test_data)
    print(f"DEBUG: Got result {result}", file=sys.stderr)
    assert result == expected
```

### Capturing Complete Call Stacks

**Python:**
```python
import traceback
stack = ''.join(traceback.format_stack())
print(f"Call stack:\n{stack}", file=sys.stderr)
```

**JavaScript/TypeScript:**
```javascript
const stack = new Error().stack;
console.error('Call stack:', stack);
```

This shows all function calls leading to the current point, making it easier to trace execution flow.

## Test Pollution Debugging

When tests fail intermittently or only when run together with other tests, you likely have test pollution—one test affecting another's state.

### Symptoms of Test Pollution

- Test passes when run alone: `pytest tests/test_file.py::test_function`
- Test fails when run with other tests: `pytest tests/`
- Test order matters (passes first, fails later)
- Tests fail inconsistently
- Global state appears modified between tests

### Binary Search for Polluting Tests

Use binary search to identify which test causes pollution:

**Step 1 - Verify isolation:**
```bash
# Run failing test alone
pytest tests/test_file.py::test_failing -v

# If it passes alone, you have pollution
```

**Step 2 - Binary search through test files:**
```bash
# Test with first half of test files
pytest tests/test_a.py tests/test_b.py tests/test_failing.py -v

# Test with second half
pytest tests/test_c.py tests/test_d.py tests/test_failing.py -v

# Narrow down which file contains polluting test
```

**Step 3 - Binary search within file:**
```bash
# Run specific test functions
pytest tests/test_a.py::test_1 tests/test_a.py::test_2 tests/test_failing.py::test_failing -v
```

**Step 4 - Isolate the culprit:**
```bash
# Once you find it
pytest tests/test_a.py::test_polluting tests/test_failing.py::test_failing -v
```

### Common Pollution Sources

**Global State:**
```python
# Test A sets global variable
def test_a():
    global_cache.clear()
    global_cache['key'] = 'value'

# Test B expects empty cache
def test_b():
    assert len(global_cache) == 0  # Fails if test_a ran first
```

**File System State:**
```python
# Test A creates files
def test_a():
    with open('test.txt', 'w') as f:
        f.write('data')
    # Forgot to clean up

# Test B assumes file doesn't exist
def test_b():
    assert not os.path.exists('test.txt')  # Fails if test_a ran first
```

**Environment Variables:**
```python
# Test A modifies environment
def test_a():
    os.environ['CONFIG'] = 'test_value'

# Test B expects default
def test_b():
    config = get_config()  # Uses os.environ['CONFIG']
    assert config == 'default'  # Fails if test_a ran first
```

**Database State:**
```python
# Test A creates records
def test_a():
    User.objects.create(username='test')
    # Forgot to clean up

# Test B expects empty database
def test_b():
    assert User.objects.count() == 0  # Fails if test_a ran first
```

### Fixing Test Pollution

**Use proper fixtures:**
```python
import pytest

@pytest.fixture
def clean_cache():
    """Ensure cache is clean before and after test"""
    global_cache.clear()
    yield
    global_cache.clear()

def test_with_cache(clean_cache):
    # Cache is guaranteed clean
    pass
```

**Use setup/teardown:**
```python
def setup_method(self):
    """Run before each test method"""
    self.temp_dir = tempfile.mkdtemp()

def teardown_method(self):
    """Run after each test method"""
    shutil.rmtree(self.temp_dir)
```

**Isolate tests properly:**
```python
@pytest.mark.usefixtures("clean_database")
def test_user_creation():
    # Database is reset before this test
    pass
```

## Multi-Layer Defense Strategy

Rather than fixing bugs at a single point, implement validation at multiple layers to prevent recurrence.

### Layered Validation Approach

**Example scenario:** Function receives empty `cwd` parameter causing git operations to fail in wrong directory.

**Layer 1 - Input validation at origin:**
```python
def get_working_directory():
    """Get working directory, never return empty string"""
    cwd = os.getcwd()
    if not cwd:
        raise ValueError("Working directory cannot be empty")
    return cwd
```

**Layer 2 - Parameter validation in caller:**
```python
def init_session(cwd: str):
    """Initialize session with working directory"""
    if not cwd:
        raise ValueError("cwd parameter cannot be empty")
    self.cwd = cwd
```

**Layer 3 - Guard at usage point:**
```python
def run_git_command(cwd: str):
    """Run git command in specified directory"""
    if not cwd or not os.path.isdir(cwd):
        raise ValueError(f"Invalid working directory: {cwd}")
    subprocess.run(['git', 'status'], cwd=cwd)
```

**Layer 4 - Type system enforcement:**
```python
from pathlib import Path

def run_git_command(cwd: Path):
    """Use Path type to ensure directory validation"""
    if not cwd.is_dir():
        raise ValueError(f"Directory does not exist: {cwd}")
    subprocess.run(['git', 'status'], cwd=str(cwd))
```

**Layer 5 - Test coverage:**
```python
def test_git_command_requires_valid_directory():
    """Ensure empty/invalid directories are rejected"""
    with pytest.raises(ValueError, match="Invalid working directory"):
        run_git_command("")

    with pytest.raises(ValueError, match="Directory does not exist"):
        run_git_command(Path("/nonexistent"))
```

### Benefits of Multi-Layer Defense

- **Fail fast:** Catch errors close to their source
- **Clear errors:** Each layer provides specific error messages
- **Redundancy:** If one layer fails, others catch the issue
- **Documentation:** Code clearly shows assumptions at each boundary
- **Impossible bugs:** Make entire classes of bugs impossible to trigger

### When to Add Layers

Add validation layers when:
- The bug originated far from where it manifested
- Multiple functions could introduce invalid state
- External data enters the system (APIs, user input, files)
- Component boundaries exist (between modules, services)
- Critical operations could have severe consequences

## Best Practices

1. **Don't assume—verify:** Test your hypotheses with evidence
2. **Document as you go:** Keep track of what you've tested
3. **Look for patterns:** Has this happened before? Are there similar bugs?
4. **Think systematically:** Don't jump to solutions before understanding root cause
5. **Consider multiple factors:** Bugs often have contributing factors, not single causes
6. **Use version control:** `git blame` and `git log` can reveal context about why code exists
7. **Instrument strategically:** Add logging BEFORE operations that might fail
8. **Trace upward:** Follow the call stack backward to find the origin
9. **Fix at the source:** Address root causes, not just symptoms
10. **Add defensive layers:** Prevent bugs at multiple architectural boundaries
