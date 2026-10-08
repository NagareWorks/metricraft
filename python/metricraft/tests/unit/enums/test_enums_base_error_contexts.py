from metricraft._legacy.enums.base import OperationEnum, FunctionEnum, ModifierEnum


def test_error_contexts_return_strings():
    class Op(OperationEnum):
        X = 'x'
    class Fn(FunctionEnum):
        Y = 'y'
    class Md(ModifierEnum):
        Z = 'z'

    assert isinstance(Op.X.operation_name, str)
    assert isinstance(Op.X.error_context, str)
    assert Fn.Y.function_name == 'y' and isinstance(Fn.Y.error_context, str)
    assert Md.Z.modifier_name == 'z' and isinstance(Md.Z.error_context, str)
