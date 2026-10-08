from metricraft._legacy.exceptions import ValidationError
from metricraft._legacy.tree.utils.validation import format_validation_errors
from metricraft._legacy.ast import Position


def test_format_validation_errors_various_paths():
    # Simulate simple string error
    out1 = format_validation_errors(["oops"])
    assert out1.startswith("Error 1: oops")

    # Simulate ValidationError without format_error_with_source
    class Dummy(ValidationError):
        def __init__(self):
            super().__init__(message="m", ast_node=None, root_node=None, context=None)
            # Emulate having a position
            self.position = Position(offset=3, length=2)
    err = Dummy()
    out2 = format_validation_errors([err])
    assert "offset:3,len:2" in out2

    # With source code path
    out3 = format_validation_errors([err], source_code="abc")
    assert out3.startswith("Error 1:")
