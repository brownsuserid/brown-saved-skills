# Planning Best Practices

This guide explains what makes a good feature plan. Plans should use **pseudocode** to show the approach, NOT full implementation code.

## Table of Contents

- [Key Principle: Plans Use Pseudocode, Not Code](#key-principle-plans-use-pseudocode-not-code)
- [Definition of Done](#definition-of-done)
- [Required Plan Structure](#required-plan-structure)
- [Pseudocode Best Practices](#pseudocode-best-practices)
- [References to Implementation Standards](#references-to-implementation-standards)
- [Plan Quality Checklist](#plan-quality-checklist)
- [Common Pitfalls to Avoid](#common-pitfalls-to-avoid)

---

## Key Principle: Plans Use Pseudocode, Not Code

During planning:
- **DO:** Use pseudocode to illustrate the approach
- **DO:** Reference libraries and explain HOW they'll be used
- **DO NOT:** Write full working code with type hints, docstrings, etc.
- **DO NOT:** Include detailed implementation code

The detailed coding standards in `../dev-shared-references/coding-standards.md` will be applied **during implementation**, not during planning.

---

## Definition of Done

Every plan starts with a Definition of Done — concrete, observable outcomes that prove the feature is complete. This is what makes a plan safe for autonomous execution: without it, there's no objective way to know when to stop.

Each criterion should be verifiable with a yes/no answer. Write in terms of observable behavior, not implementation tasks.

**Examples of good vs bad criteria:**

| Bad (Vague) | Good (Specific) |
|-------------|-----------------|
| "User can log in" | "User enters email/password on /login, receives JWT token, is redirected to /dashboard" |
| "Handle errors gracefully" | "Invalid email format shows 'Please enter a valid email address' below the input field" |
| "API works correctly" | "POST /api/users with valid payload returns 201 and user object with id, email, created_at" |
| "Tests are written" | "test_create_user_with_valid_email_returns_user_object passes with email='test@example.com'" |

See the full template in `../templates/feature-plan-template.md`.

---

## Required Plan Structure

Every feature plan should include these components in this order:

### 1. Definition of Done
At the very top. Concrete, observable completion criteria with acceptance scenarios.

### 2. Overview
- **Feature Summary:** Brief description of what's being built
- **Business Value:** Why this feature matters
- **Success Criteria:** How we'll know it's done correctly

### 3. Setup & Preparation

```
STEP: Create Git Worktree
- Use ~/scripts/wt.sh to create new worktree: feature/user-authentication
- Ensures development happens in an isolated directory
```

### 4. Test-Driven Development Foundation

Tests come before implementation because retrofitting tests after writing code tends to miss edge cases — you unconsciously write tests that match what you already built rather than what should be built.

```
STEP: Create Unit Tests (BEFORE implementation)
- tests/test_auth.py:

  pseudocode:
  test_successful_login():
      - Given valid credentials (email="user@example.com", password="correct")
      - When user attempts login
      - Then return JWT token and 200 status

  test_invalid_credentials():
      - Given invalid password (email="user@example.com", password="wrong")
      - When user attempts login
      - Then raise AuthenticationError with message "Invalid credentials"
      - Return 401 status

  test_missing_user():
      - Given non-existent email (email="nobody@example.com")
      - When user attempts login
      - Then raise UserNotFoundError
      - Return 404 status
```

### 5. Implementation Plan with Pseudocode

Be specific about:
- **Libraries:** Which specific libraries and why
- **File Organization:** Where code will live
- **HOW:** Approach using pseudocode

Example:

```
STEP: Implement JWT Authentication

Libraries:
- python-jose for JWT encoding/decoding
- passlib with bcrypt for password hashing
- FastAPI's OAuth2PasswordBearer for token management

File Structure:
- app/auth/jwt.py - Token creation and validation
- app/auth/password.py - Password hashing utilities
- app/api/endpoints/auth.py - Login/logout endpoints

Pseudocode for jwt.py:
  function create_access_token(user_id, expiration):
      data = {user_id, expiration_timestamp}
      encoded_jwt = jose.jwt.encode(data, SECRET_KEY, algorithm="HS256")
      return encoded_jwt

  function verify_token(token):
      try:
          payload = jose.jwt.decode(token, SECRET_KEY)
          return payload.user_id
      catch JWTError:
          raise unauthorized_error

Implementation will follow standards in ../dev-shared-references/coding-standards.md
```

### 6. Observability & Structured Logging

Every feature needs to be observable in production. Plan for:
- JSON structured logging with correlation IDs
- Key metrics (request count, error rate, latency percentiles)
- CloudWatch alarms on error rate spikes and latency degradation

### 7. Code Quality Checks

Include language-appropriate quality checks. For Python projects:

```
STEP: Code Quality & Security Checks
- Run ruff check (linting)
- Run ruff format (code formatting)
- Run mypy (type checking)
- Run bandit (security scanning)
- Fix any issues found
```

For other languages, include equivalent tooling (e.g., ESLint/Prettier for TypeScript, clippy for Rust).

### 8. Integration Testing

```
STEP: End-to-End Integration Tests
- Create tests/integration/test_auth_flow.py

  pseudocode:
  test_complete_auth_flow():
      - Register new user
      - Login with credentials
      - Verify JWT token received
      - Access protected endpoint with token
      - Verify authorization works

  test_token_expiration():
      - Login and get token
      - Wait for expiration
      - Attempt to access protected endpoint
      - Verify 401 unauthorized response
```

### 9. Documentation Updates

```
STEP: Update Documentation
- Update API docs with new endpoints and request/response examples
- Update README with setup instructions and environment variables
```

### 10. User Testing Instructions

```
STEP: Lead Developer Testing
Provide clear test scenarios with expected outcomes:

1. Test successful login:
   - Navigate to /login
   - Enter valid credentials
   - Verify token returned
   - Verify can access protected routes

2. Test invalid credentials:
   - Enter wrong password
   - Verify error message shown
   - Verify no token returned
```

### 11. Git Commit & PR

```
STEP: Commit and Create PR (ONLY after all tests pass)

Prerequisites:
- All unit tests passing
- All integration tests passing
- Quality checks passing
- Lead developer has tested and approved

Commit message (following git-conventions.md):
  feat: add JWT-based user authentication system

Create PR:
- Push to feature/user-authentication branch
- Never push directly to main
- Create PR with detailed description
```

---

## Pseudocode Best Practices

### Good Pseudocode Examples

```
GOOD - Shows approach without implementation details:

function authenticate_user(email, password):
    user = database.find_user_by_email(email)
    if not user:
        raise UserNotFound
    if not password_matches(password, user.hashed_password):
        raise InvalidCredentials
    return create_session_token(user.id)
```

```
BAD - Full implementation code (save for implementation phase):

def authenticate_user(email: str, password: str) -> str:
    """Authenticate a user and return a session token.

    Args:
        email: User's email address
        password: User's plain text password

    Returns:
        JWT session token

    Raises:
        UserNotFound: If email doesn't exist
        InvalidCredentials: If password is wrong
    """
    user = await db.query(User).filter_by(email=email).first()
    if not user:
        raise UserNotFound(f"No user found with email {email}")
    # ... full implementation with type hints, docstrings, etc.
```

---

## References to Implementation Standards

When writing the plan, include references to the standards that will be applied during implementation:

```
Implementation will follow:
- Language standards in ../dev-shared-references/coding-standards.md (type hints, docstrings, testing)
- Git conventions in ../dev-shared-references/git-conventions.md (commit message format)
- AWS standards in ../dev-shared-references/aws-standards.md (if deploying to AWS)
- Dependency management per ../dev-shared-references/uv-guide.md (Python projects)
```

---

## Plan Quality Checklist

Before finalizing a plan, verify it includes:

- [ ] Definition of Done at the top with observable completion criteria
- [ ] Acceptance scenarios with concrete values
- [ ] Out of scope section explicitly listing what's NOT included
- [ ] Overview with business value and success criteria
- [ ] Git worktree creation step
- [ ] Unit test creation as an early step (TDD approach)
- [ ] Specific libraries identified with justification
- [ ] Pseudocode showing approach (NOT full implementation code)
- [ ] File organization and structure clearly defined
- [ ] Code quality checks step (language-appropriate tooling)
- [ ] Integration testing step
- [ ] Documentation update step
- [ ] User/lead developer testing step with scenarios
- [ ] Commit and PR creation as final step
- [ ] References to implementation standards

---

## Common Pitfalls to Avoid

### DON'T: Write Full Implementation Code in Plans

Plans should explain the approach with pseudocode, not provide ready-to-run code.

### DON'T: Skip Test Planning

Tests should be planned BEFORE implementation steps (TDD). Retrofitting tests after the fact tends to produce tests that validate the implementation rather than the requirements.

### DON'T: Be Vague About Libraries

Instead of "use a JWT library", specify "use python-jose for JWT encoding/decoding because it supports the algorithms we need and is actively maintained."

### DON'T: Forget Quality Checks

All plans should include linting, formatting, type checking, and security scanning steps appropriate to the project's language and toolchain.

### DON'T: Use Vague Completion Criteria

"Works correctly" and "handles errors gracefully" are not verifiable. Specify exact inputs, outputs, error messages, and observable behaviors.

### DO: Explain the Approach

Use pseudocode to show HOW the feature will work, not just WHAT will be built.

### DO: Think Through Edge Cases

Include edge cases and error scenarios in both unit and integration test plans, with specific input values and expected outcomes.

### DO: Consider the Developer Experience

Provide clear testing instructions so the lead developer knows exactly what to verify.
