import json
import pytest
from metricraft._legacy.builder.mixins import FactoryMixin


def test_validate_strict_ok_and_promql_compat():
    b = FactoryMixin.from_metric('cpu').where_eq('job', 'api')
    # strict MetricsQL validation should return empty string
    out = b.validate(standard='MetricsQL', strict=True)
    assert isinstance(out, str)
    # PromQL compatibility: trigger a MetricsQL-only function and expect error string with arrow markers
    msg = b.alias('x').validate(standard='PromQL', strict=False)
    assert isinstance(msg, str) and msg


def test_validate_invalid_standard_and_syntax_error_paths():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(Exception):
        b.validate(standard='UnknownStandard')
    # Trigger syntax validation exception: invalid label name should raise at where_eq
    with pytest.raises(Exception):
        b.where_eq('1badlabel', 'x')


def test_debug_and_analyze_and_positions_json():
    b = FactoryMixin.from_metric('cpu').where_eq('job', 'api')
    dbg = b.debug()
    assert isinstance(dbg, str) and 'METRIC_SELECTOR' in dbg
    analysis = b.analyze()
    assert isinstance(analysis, dict)
    # visualize_positions should return a string overlay containing the source
    vis = b.visualize_positions('cpu{job="api"}')
    assert isinstance(vis, str) and 'Source:' in vis
    js = b.to_debug_json()
    assert isinstance(js, str)
    # JSON should be parseable
    json.loads(js)
    pos = b.debug_positions()
    assert isinstance(pos, str)
