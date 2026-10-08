from metricraft._legacy.exceptions import VMPositionalError, VMInvalidExpressionError


def test_invalid_expression_error_str():
    err = VMInvalidExpressionError("op")
    # Message formatting path
    assert "op" in str(err)


def test_vm_positional_error_fallbacks():
    e = VMPositionalError("msg")
    # No ast/root set -> None
    assert e.calculate_absolute_position() is None