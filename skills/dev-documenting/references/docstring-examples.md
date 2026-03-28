# Docstring Examples Reference

This document provides comprehensive examples of Google-style docstrings for different types of code. All docstrings follow an **agent-first** philosophy: assume every function may be called by an AI agent as a tool. Include concrete example values, explicit constraints, and return structure so an agent can call the function correctly without reading the implementation.

## Agent-First Patterns

When writing parameter descriptions, prefer concrete over abstract:

| Instead of | Write |
|-----------|-------|
| `user_id: The user identifier` | `user_id: Unique user identifier (e.g., "usr_abc123")` |
| `rate: The discount rate` | `rate: Discount as decimal between 0.0 and 1.0 (e.g., 0.2 for 20% off)` |
| `tags: List of tags` | `tags: Filter tags (e.g., ["electronics", "sale"]). Empty list matches nothing` |
| `Returns: The result` | `Returns: Dict with keys "total" (float), "items" (list[str]), "status" ("ok" or "error")` |

For Raises sections, include recovery guidance:

| Instead of | Write |
|-----------|-------|
| `ValueError: If rate is invalid` | `ValueError: If rate is not between 0.0 and 1.0. Pass rate as decimal, not percentage` |
| `FileNotFoundError: If file missing` | `FileNotFoundError: If file not found at path. Verify path exists before calling` |

---

## Function Docstrings

### Simple Function

```python
def calculate_discount(price: float, rate: float) -> float:
    """Calculate discounted price.

    Applies a percentage discount rate to the original price.
    The discount rate should be expressed as a decimal (0.0 to 1.0),
    where 0.2 represents a 20% discount.

    Args:
        price: Original price in dollars. Must be non-negative.
        rate: Discount rate as decimal between 0.0 and 1.0.
              For example, 0.2 means 20% off.

    Returns:
        Final price after applying the discount.

    Raises:
        ValueError: If price is negative
        ValueError: If rate is not between 0.0 and 1.0

    Examples:
        >>> calculate_discount(100.0, 0.2)
        80.0

        >>> calculate_discount(50.0, 0.0)
        50.0

        >>> calculate_discount(75.0, 1.0)
        0.0

    Note:
        This function does not round the result. Caller is responsible
        for rounding to appropriate precision (e.g., 2 decimal places
        for currency).
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= rate <= 1:
        raise ValueError("Rate must be between 0 and 1")
    return price * (1 - rate)
```

### Complex Function with Multiple Returns

```python
def process_order(order: Order) -> tuple[PaymentResult, Optional[str]]:
    """Process order payment and return result.

    Validates order, processes payment, and sends confirmation.
    Returns both payment result and optional error message.

    Args:
        order: Order to process. Must have valid payment_method
               and at least one item.

    Returns:
        Tuple of (payment_result, error_message):
        - payment_result: PaymentResult with status and transaction_id
        - error_message: Error description if payment failed, None if successful

    Raises:
        ValueError: If order is missing required fields
        PaymentGatewayError: If payment gateway is unreachable

    Examples:
        >>> order = Order(user=user, items=[item], payment_method=card)
        >>> result, error = process_order(order)
        >>> if error is None:
        ...     print(f"Success: {result.transaction_id}")
        ... else:
        ...     print(f"Failed: {error}")

    Note:
        This function is idempotent. Calling multiple times with the
        same order will not result in duplicate charges.
    """
    # Implementation
```

### Async Function

```python
async def fetch_user_data(user_id: int) -> dict[str, Any]:
    """Fetch user data asynchronously from database.

    Retrieves complete user profile including preferences and
    activity history. Uses connection pooling for efficiency.

    Args:
        user_id: Unique identifier for user

    Returns:
        Dictionary containing user data:
        - id: User ID
        - username: User's username
        - email: User's email address
        - preferences: User preferences dict
        - activity: Recent activity list

    Raises:
        UserNotFoundError: If user_id doesn't exist
        DatabaseError: If database connection fails

    Examples:
        >>> user_data = await fetch_user_data(123)
        >>> print(user_data['username'])
        'john_doe'

    Note:
        This function uses async database operations.
        Must be called with await from async context.
    """
    # Implementation
```

---

## Class Docstrings

### Simple Class

```python
class User:
    """Represent a user in the system.

    This class models user accounts with authentication and
    profile information. Users can have multiple roles and
    belong to organizations.

    Attributes:
        id: Unique user identifier
        username: User's login username
        email: User's email address
        is_active: Whether user account is active
        created_at: Timestamp of account creation

    Examples:
        >>> user = User(username="john", email="john@example.com")
        >>> print(user.username)
        'john'

        >>> user.deactivate()
        >>> print(user.is_active)
        False
    """

    def __init__(self, username: str, email: str):
        """Initialize user with username and email.

        Args:
            username: Unique username for login
            email: User's email address

        Raises:
            ValueError: If username or email is empty
        """
        self.username = username
        self.email = email
```

### Complex Class with Configuration

```python
class PaymentProcessor:
    """Process payments through various payment gateways.

    This class handles payment processing, including validation,
    charging payment methods, handling retries, and error management.
    It supports multiple payment gateways (Stripe, PayPal, etc.) through
    a gateway interface.

    Attributes:
        gateway: Payment gateway instance implementing PaymentGateway interface
        retry_attempts: Number of times to retry failed payments (default: 3)
        timeout: Maximum time in seconds to wait for gateway response (default: 30)

    Examples:
        >>> processor = PaymentProcessor(gateway=StripeGateway())
        >>> result = processor.process_payment(order, payment_method)
        >>> print(result.status)
        'completed'

        >>> # With custom retry configuration
        >>> processor = PaymentProcessor(
        ...     gateway=PayPalGateway(),
        ...     retry_attempts=5,
        ...     timeout=60
        ... )

    Note:
        Payment gateway must be properly configured with API credentials
        before creating PaymentProcessor instance. See gateway documentation
        for required environment variables.
    """

    def __init__(
        self,
        gateway: PaymentGateway,
        retry_attempts: int = 3,
        timeout: int = 30
    ):
        """Initialize payment processor.

        Args:
            gateway: Payment gateway to use for processing
            retry_attempts: Number of retry attempts for failed payments.
                           Must be >= 0.
            timeout: Gateway request timeout in seconds. Must be positive.

        Raises:
            ValueError: If retry_attempts is negative
            ValueError: If timeout is not positive
        """
        # Implementation
```

---

## Module Docstrings

```python
"""User service module.

This module provides user management functionality including:
- User creation and authentication
- Profile management
- Email verification
- Password reset

Example:
    >>> from app.services.user import UserService
    >>> service = UserService()
    >>> user = service.create_user("john", "john@example.com", "password")
    >>> service.send_verification_email(user)
"""

from typing import Optional
from app.models import User


class UserService:
    """Service for managing user accounts."""
    # Implementation
```

---

## Before/After Examples

### Undocumented → Documented

**Before:**
```python
def calculate_discount(price, rate):
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= rate <= 1:
        raise ValueError("Rate must be between 0 and 1")
    return price * (1 - rate)
```

**After:**
```python
def calculate_discount(price: float, rate: float) -> float:
    """Calculate discounted price.

    Applies a percentage discount rate to the original price.
    The discount rate should be expressed as a decimal (0.0 to 1.0),
    where 0.2 represents a 20% discount.

    Args:
        price: Original price in dollars. Must be non-negative.
        rate: Discount rate as decimal between 0.0 and 1.0.

    Returns:
        Final price after applying the discount.

    Raises:
        ValueError: If price is negative
        ValueError: If rate is not between 0.0 and 1.0

    Examples:
        >>> calculate_discount(100.0, 0.2)
        80.0
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not 0 <= rate <= 1:
        raise ValueError("Rate must be between 0 and 1")
    return price * (1 - rate)
```

### Poor Docstring → Good Docstring

**Before:**
```python
def get_full_name(self):
    """Get name."""
    return f"{self.first_name} {self.last_name}"
```

**After:**
```python
def get_full_name(self) -> str:
    """Get user's full name, handling missing values.

    Combines first and last name with proper spacing.
    Handles None or empty values gracefully.

    Returns:
        Full name with first and last name, or empty string
        if both are missing. Strips extra whitespace.

    Examples:
        >>> user = User(first_name="John", last_name="Doe")
        >>> user.get_full_name()
        'John Doe'

        >>> user = User(first_name=None, last_name="Doe")
        >>> user.get_full_name()
        'Doe'
    """
    first = self.first_name or ""
    last = self.last_name or ""
    return f"{first} {last}".strip()
```

---

## README Structure Examples

### Minimal README

```markdown
# Project Name

Brief one-sentence description.

## Installation

```bash
pip install package-name
```

## Quick Start

```python
from package import Client

client = Client()
result = client.do_something()
```

## Documentation

Full docs: https://project.readthedocs.io
```

### Complete README

```markdown
# Project Name

Brief one-sentence description.

## Overview

1-2 paragraphs explaining what this does and why.

## Features

- Key feature 1
- Key feature 2
- Key feature 3

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL 15+

### Install

```bash
pip install package-name
```

## Quick Start

```python
from package import Client

client = Client(api_key="your_key")
result = client.process(data)
```

## Usage

### Common Task 1

```python
# Example for task 1
```

### Common Task 2

```python
# Example for task 2
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| API_KEY | Your API key | Required |

## Development

```bash
# Setup
git clone repo
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT License

## Support

- Issues: github.com/user/project/issues
- Email: support@project.com
```

---

## Usage Examples Document

```markdown
# Usage Examples

## User Management

### Creating a User

```python
from app.services import UserService

service = UserService()
user = service.create_user(
    username="john_doe",
    email="john@example.com",
    password="secure_password"
)
```

### Authenticating

```python
from app.services import AuthenticationService

auth = AuthenticationService()
token = auth.authenticate("john_doe", "password")
```

## Error Handling

### Handling User Errors

```python
from app.exceptions import InvalidEmailError

try:
    user = service.create_user(...)
except InvalidEmailError as e:
    print(f"Invalid email: {e}")
```
```

---

## Summary

**Key docstring elements:**
- Brief one-line summary
- Detailed explanation
- Args with types and constraints
- Returns with structure
- Raises with conditions
- Examples that work
- Notes for important caveats

**Testing docstrings:**
```bash
python -m doctest module.py
```
