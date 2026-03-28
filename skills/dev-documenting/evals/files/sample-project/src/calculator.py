from typing import Optional


class Calculator:
    def __init__(self, precision: int = 2):
        self.precision = precision
        self._history: list[tuple[str, float]] = []

    def add(self, a: float, b: float) -> float:
        result = round(a + b, self.precision)
        self._history.append(("add", result))
        return result

    def subtract(self, a: float, b: float) -> float:
        result = round(a - b, self.precision)
        self._history.append(("subtract", result))
        return result

    def multiply(self, a: float, b: float) -> float:
        result = round(a * b, self.precision)
        self._history.append(("multiply", result))
        return result

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = round(a / b, self.precision)
        self._history.append(("divide", result))
        return result

    def get_history(self) -> list[tuple[str, float]]:
        return self._history.copy()

    def clear_history(self) -> None:
        self._history.clear()


def calculate_compound_interest(
    principal: float,
    rate: float,
    years: int,
    compounds_per_year: int = 12,
) -> dict[str, float]:
    if principal < 0:
        raise ValueError("Principal must be non-negative")
    if rate < 0:
        raise ValueError("Rate must be non-negative")
    if years < 0:
        raise ValueError("Years must be non-negative")

    amount = principal * (1 + rate / compounds_per_year) ** (compounds_per_year * years)
    interest = amount - principal
    return {
        "principal": principal,
        "rate": rate,
        "years": years,
        "final_amount": round(amount, 2),
        "interest_earned": round(interest, 2),
    }


def parse_expression(expr: str) -> Optional[float]:
    allowed = set("0123456789.+-*/() ")
    if not all(c in allowed for c in expr):
        return None
    try:
        result = eval(expr)  # noqa: S307
        return float(result)
    except Exception:
        return None
