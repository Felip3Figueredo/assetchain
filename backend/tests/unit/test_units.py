from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.domain.units import from_wei, to_wei


def test_to_wei_and_back():
    assert to_wei(Decimal("100000")) == 100_000 * 10**18
    assert from_wei(10**18 + 5 * 10**17) == Decimal("1.5")


@pytest.mark.parametrize("bad", [Decimal("0"), Decimal("-1"), Decimal("0.0000000000000000001")])
def test_to_wei_rejects_invalid(bad):
    with pytest.raises(AppError) as exc:
        to_wei(bad)
    assert exc.value.status_code == 422
