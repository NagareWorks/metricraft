import pytest

from metricraft._legacy.exceptions.utils import require_expression
from metricraft._legacy.exceptions.builder import PositionalError


def test_require_expression_raises_positional_error():
    with pytest.raises(PositionalError) as ei:
        require_expression("rate")
    assert "Cannot perform 'rate'" in str(ei.value)
