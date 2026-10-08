import pytest
from metricraft._legacy.exceptions import InvalidParameterError
from metricraft._legacy.builder.mixins import FactoryMixin

# Transformation mixin core paths

def test_parenthesize_and_bool_and_timestamp():
    b = FactoryMixin.from_metric('cpu').where_eq('host', 'a')
    p = b.parenthesize()
    assert p is not None
    bl = b.gt(0).bool()
    assert bl is not None
    ts = b.timestamp()
    assert ts is not None


def test_clamp_min_max_and_alias_sort():
    b = FactoryMixin.from_metric('cpu')
    cmin = b.clamp_min(0.1)
    cmax = b.clamp_max(1.0)
    assert cmin is not None and cmax is not None
    ali = b.alias('my_metric')
    assert ali is not None
    s = b.sort('asc')
    sd = b.sort_desc()
    assert s is not None and sd is not None


def test_label_replace_join_set_and_errors():
    b = FactoryMixin.from_metric('cpu').where_eq('job', 'api')
    lr = b.label_replace('svc', '$1', 'job', r'(.*)')
    assert lr is not None
    lj = b.label_join('full', '-', 'job', 'instance')
    assert lj is not None
    ls = b.label_set(team='core', env='prod')
    assert ls is not None
    ld = b.label_del('job')
    assert ld is not None
    with pytest.raises(ValueError):
        b.label_join('x', '-', *())  # no source labels
    with pytest.raises(InvalidParameterError):
        b.label_del()
    with pytest.raises(InvalidParameterError):
        b.label_del('')  # empty label invalid
    sb = b.sort_by_label('job')
    sb_desc = b.sort_by_label_desc('job')
    sb_num = b.sort_by_label_numeric('instance')
    sb_num_desc = b.sort_by_label_numeric_desc('instance')
    assert sb and sb_desc and sb_num and sb_num_desc

    # Test multiple label arguments
    sb_multi = b.sort_by_label('job', 'instance', 'env')
    sb_desc_multi = b.sort_by_label_desc('job', 'instance')
    sb_num_multi = b.sort_by_label_numeric('port', 'instance')
    sb_num_desc_multi = b.sort_by_label_numeric_desc('port', 'job', 'env')
    assert sb_multi and sb_desc_multi and sb_num_multi and sb_num_desc_multi

    # Test error cases
    with pytest.raises(InvalidParameterError):
        b.sort_by_label('  ')
    with pytest.raises(InvalidParameterError):
        b.sort_by_label_numeric('')
    with pytest.raises(InvalidParameterError):
        b.sort_by_label()  # No arguments
    with pytest.raises(InvalidParameterError):
        b.sort_by_label_desc()  # No arguments


def test_union_and_limit_and_outliers_and_subquery_and_keep_names():
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')
    u = a.union(b)
    assert u is not None
    km = a.keep_metric_names()
    assert km is not None
    lk = a.limitk(5)
    ok = a.outliersk(3)
    assert lk is not None and ok is not None
    sq = a.subquery('5m')
    assert sq is not None

# Time range mixin

def test_offset_and_at():
    b = FactoryMixin.from_metric('cpu')
    off = b.offset('5m')
    assert off is not None
    at1 = b.at(1640995200)
    at2 = b.at('2022-01-01T00:00:00Z')
    assert at1 is not None and at2 is not None

# Mathematical mixin (hit a representative set)

def test_mathematical_functions_subset():
    b = FactoryMixin.from_metric('cpu')
    assert b.abs() is not None
    assert b.ceil() is not None
    assert b.floor() is not None
    assert b.round() is not None
    assert b.sqrt() is not None
    assert b.exp() is not None
    assert b.ln() is not None
    assert b.log2() is not None
    assert b.log10() is not None
    assert b.sin() is not None
    assert b.cos() is not None
    assert b.tan() is not None
    assert b.asin() is not None
    assert b.acos() is not None
    assert b.atan() is not None
    assert b.atan2(2.0) is not None
    assert b.sinh() is not None
    assert b.cosh() is not None
    assert b.tanh() is not None
    assert b.asinh() is not None
    assert b.acosh() is not None
    assert b.atanh() is not None
    assert b.deg() is not None
    assert b.rad() is not None

# Comparison between

def test_between_valid_and_invalid():
    b = FactoryMixin.from_metric('cpu')
    ok = b.between(0.1, 0.9)
    assert ok is not None
    with pytest.raises(Exception):
        b.between(1.0, 0.5)  # min>max

# Range vector functions

def test_range_functions_core_and_over_time():
    b = FactoryMixin.from_metric('cpu')
    assert b.range('5m') is not None
    assert b.rate('5m') is not None
    assert b.irate('5m') is not None
    assert b.idelta('5m') is not None
    assert b.increase('5m') is not None
    assert b.delta('5m') is not None
    assert b.changes('5m') is not None
    assert b.resets('5m') is not None
    assert b.avg_over_time('5m') is not None
    assert b.max_over_time('5m') is not None
    assert b.min_over_time('5m') is not None
    assert b.sum_over_time('5m') is not None
    assert b.count_over_time('5m') is not None
    assert b.stddev_over_time('5m') is not None
    assert b.stdvar_over_time('5m') is not None
    assert b.last_over_time('5m') is not None
    assert b.present_over_time('5m') is not None
    assert b.deriv('5m') is not None
    assert b.mad_over_time('5m') is not None
    assert b.median_over_time('5m') is not None
    assert b.mode_over_time('5m') is not None
    assert b.rate_over_sum('5m') is not None
    assert b.zscore_over_time('5m') is not None


def test_quantile_over_time_and_holt_winters_and_predict_linear():
    b = FactoryMixin.from_metric('cpu')
    # valid
    assert b.quantile_over_time(0.95, '5m') is not None
    assert b.holt_winters('5m', 0.3, 0.3) is not None
    assert b.predict_linear(60.0, '5m') is not None
    # invalid params
    with pytest.raises(Exception):
        b.quantile_over_time(1.5, '5m')
    with pytest.raises(Exception):
        b.holt_winters('5m', -0.1, 0.3)
    with pytest.raises(Exception):
        b.holt_winters('5m', 0.3, 1.5)
