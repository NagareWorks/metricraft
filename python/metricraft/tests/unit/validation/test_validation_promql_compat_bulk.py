import pytest

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.utils import templates as T


@pytest.mark.parametrize(
    "fname",
    [
    # MetricsQL-only functions (a sample is enough to cover loop logic)
        'label_set', 'label_del', 'label_copy', 'label_move', 'label_transform',
        'label_uppercase', 'label_lowercase', 'alias', 'union', 'limitk',
        'outliersk', 'mad_over_time', 'mode_over_time', 'range_over_time',
        'running_sum', 'running_max', 'running_min', 'running_avg', 'rollup',
        'rollup_rate', 'rollup_deriv', 'rollup_delta', 'rollup_increase',
        'rollup_candlestick', 'smooth_exponential', 'remove_resets',
        'increases_over_time', 'decreases_over_time', 'share_le_over_time',
        'share_gt_over_time', 'count_le_over_time', 'count_gt_over_time',
        'buckets_limit', 'histogram_avg', 'histogram_stddev', 'histogram_stdvar',
        'prometheus_buckets', 'vmrange_buckets',
    ],
)
def test_promql_compatibility_flags_metricsql_functions(fname: str):
    b = FactoryMixin.from_metric('m')
    # Use generic template to construct function call and ensure fname( appears in the query string
    expr = T.create_function_with_args(b, fname, [])
    msg = expr.validate(standard='PromQL', strict=False)
    assert isinstance(msg, str) and 'PromQL compatibility error' in msg


@pytest.mark.parametrize(
    ("method_name", "labels"),
    [
        ('sort_by_label', ['job']),
        ('sort_by_label', ['job', 'instance']),
        ('sort_by_label_desc', ['job']),
        ('sort_by_label_desc', ['job', 'instance', 'env']),
        ('sort_by_label_numeric', ['instance']),
        ('sort_by_label_numeric', ['port', 'instance']),
        ('sort_by_label_numeric_desc', ['instance']),
        ('sort_by_label_numeric_desc', ['port', 'job', 'env']),
    ],
)
def test_promql_sort_by_label_functions(method_name: str, labels: list):
    """Test sort_by_label functions with single and multiple arguments for PromQL compatibility."""
    b = FactoryMixin.from_metric('m')
    expr = getattr(b, method_name)(*labels)
    msg = expr.validate(standard='PromQL', strict=False)
    assert isinstance(msg, str) and 'PromQL compatibility error' in msg


def test_promql_compatibility_flags_metricsql_modifier_keep_metric_names():
    b = FactoryMixin.from_metric('m').keep_metric_names()
    msg = b.validate(standard='PromQL', strict=False)
    assert isinstance(msg, str) and 'PromQL compatibility error' in msg
