import re
import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.exceptions import VMPositionalError
from metricraft._legacy.visitor import get_query_visitor, PositionTrackingVisitor


def _build_selector():
    b = FactoryMixin.from_metric("cpu").where_eq("job", "api").where_eq("instance", "host:9100")
    root = b.ast_node
    assert root is not None
    label_job = root.label_matchers[0]
    label_inst = root.label_matchers[1]
    return b, root, label_job, label_inst


def test_vm_positional_error_label_value_arrow():
    b, root, label_job, _ = _build_selector()
    query = get_query_visitor().visit(root)

    # Message containing the target label name enables special label value positioning
    err = VMPositionalError(
        message="Invalid label value for 'job': does not match pattern",
        ast_node=label_job.value_node,
        root_node=root,
    )
    # Leverage automatic arrow formatting via __str__ by setting source
    err.set_source_query(query)
    s = str(err)
    # Should include source pointer arrows and the label pattern
    assert 'job="api"' in query
    assert '^' in s


def test_vm_positional_error_generic_node_position_map():
    b, root, label_job, _ = _build_selector()
    query = get_query_visitor().visit(root)

    # Use the LabelMatcher node to exercise PositionTrackingVisitor map path
    err = VMPositionalError(
        message="Some validation on matcher",
        ast_node=label_job,
        root_node=root,
    )
    formatted = err.format_error_with_source(query)
    # Either arrows or absolute char range should be present
    assert ('^' in formatted) or (re.search(r"Absolute position: chars \d+-\d+", formatted) is not None)


@pytest.mark.parametrize("missing_pattern", [
    "Invalid label value",  # no label name present
    "Invalid label value for 'unknown'",  # different label name
])
def test_vm_positional_error_label_value_fallback_when_pattern_missing(missing_pattern: str):
    b, root, label_job, _ = _build_selector()
    query = get_query_visitor().visit(root)

    # Without the precise pattern, code should gracefully fallback (non-crashing) and still return a message
    err = VMPositionalError(
        message=missing_pattern,
        ast_node=label_job.value_node,
        root_node=root,
    )
    msg = err.format_error_with_source(query)
    assert isinstance(msg, str) and msg


def test_position_tracking_visitor_maps_inner_string_literal_precisely():
    b, root, label_job, label_inst = _build_selector()
    query = get_query_visitor().visit(root)

    # Build the position map and verify we can slice the query by recorded positions
    v = PositionTrackingVisitor()
    pos_map = v.build_position_map(root)

    # Ensure core nodes were tracked
    assert id(root) in pos_map
    assert id(label_job) in pos_map
    assert id(label_job.value_node) in pos_map

    start, end = pos_map[id(label_job.value_node)]
    # The mapping for inner StringLiteral should cover only the content (without quotes)
    assert query[start:end] == "api"

    # Also verify the second matcher content mapping
    s2, e2 = pos_map[id(label_inst.value_node)]
    assert query[s2:e2] == "host:9100"
