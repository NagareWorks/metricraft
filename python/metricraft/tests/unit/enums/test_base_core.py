"""Core tests for enums.base helpers."""

from enum import Enum
from metricraft._legacy.enums.base import OperationEnum, FunctionEnum, ModifierEnum


class Op(OperationEnum):
    ADD = "+"

    @property
    def operation_name(self) -> str:
        return "add"


class Fn(FunctionEnum):
    RATE = "rate"


class Md(ModifierEnum):
    BY = "by"


def test_operation_enum_context():
    assert Op.ADD.error_context == "add operation"
    # default implementation path (value used)
    class Op2(OperationEnum):
        SUB = "-"
    assert Op2.SUB.error_context.endswith("operation")


def test_function_enum_context():
    assert Fn.RATE.error_context == "rate() function"


def test_modifier_enum_context():
    assert Md.BY.error_context == "by modifier"
