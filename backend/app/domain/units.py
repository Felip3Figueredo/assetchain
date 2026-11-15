from decimal import Decimal

from app.core.errors import AppError

DECIMALS = 18
_UNIT = 10**DECIMALS


def to_wei(amount: Decimal) -> int:
    """Whole-token decimal -> smallest unit. Rejects <= 0 and more than 18 decimal places."""
    if amount <= 0:
        raise AppError(422, "INVALID_AMOUNT", "Amount must be greater than zero")
    scaled = amount * _UNIT
    if scaled != scaled.to_integral_value():
        raise AppError(422, "INVALID_AMOUNT", f"Amount supports at most {DECIMALS} decimal places")
    return int(scaled)


def from_wei(value: int) -> Decimal:
    return Decimal(value) / _UNIT


def fmt(value: int) -> str:
    """Wei -> plain decimal string in whole tokens (e.g. '100000', '1.5')."""
    d = from_wei(value)
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s
