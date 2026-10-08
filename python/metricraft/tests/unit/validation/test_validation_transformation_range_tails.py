import pytest
from unittest.mock import patch

from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.exceptions import VMInvalidExpressionError
from metricraft._legacy.exceptions import InvalidParameterError


def test_validation_invalid_standard_and_empty_ast_paths():
    b = FactoryMixin.from_metric('cpu')
    # invalid standard
    with pytest.raises(InvalidParameterError):
        _ = b.validate(standard='FooQL')

    # empty ast paths for debug helpers -> _create_new_builder(None, ...) raises ValueError
    with pytest.raises(ValueError):
        FactoryMixin.from_metric('cpu')._create_new_builder(None, b._sign_state).debug()
    with pytest.raises(ValueError):
        FactoryMixin.from_metric('cpu')._create_new_builder(None, b._sign_state).to_debug_json()
    with pytest.raises(ValueError):
        FactoryMixin.from_metric('cpu')._create_new_builder(None, b._sign_state).debug_positions()
    with pytest.raises(ValueError):
        FactoryMixin.from_metric('cpu')._create_new_builder(None, b._sign_state).visualize_positions('cpu')


def test_validation_promql_compat_arrows_for_functions_and_modifiers():
    # trigger MetricsQL-only function
    msg = FactoryMixin.from_metric('x').label_set(team='core').validate(standard='PromQL')
    assert 'PromQL compatibility error' in msg and 'label_set' in msg
    msg_del = FactoryMixin.from_metric('x').label_del('job').validate(standard='PromQL')
    assert 'PromQL compatibility error' in msg_del and 'label_del' in msg_del
    # trigger MetricsQL-only modifier (keep_metric_names)
    msg2 = FactoryMixin.from_metric('x').sum().keep_metric_names().validate(standard='PromQL')
    assert 'keep_metric_names' in msg2 and '^' in msg2  # arrow underline present


def test_transformation_sort_and_errors():
    b = FactoryMixin.from_metric('cpu')
    _ = b.sort()
    _ = b.sort_desc()
    with pytest.raises(InvalidParameterError):
        b.sort('zzz')


def test_transformation_label_join_and_label_set_errors():
    b = FactoryMixin.from_metric('cpu')
    with pytest.raises(ValueError):
        b.label_join('k', ',')  # no source labels
    with pytest.raises(InvalidParameterError):
        b.label_set()  # empty labels


def test_transformation_moving_average_and_smooth_exponential_bounds():
    b = FactoryMixin.from_metric('cpu')
    _ = b.moving_average('5m')
    with pytest.raises(InvalidParameterError):
        b.smooth_exponential(-0.1)
    with pytest.raises(InvalidParameterError):
        b.smooth_exponential(1.1)


def test_range_vector_functions_tails_and_errors():
    b = FactoryMixin.from_metric('x')
    # happy paths cover helper dispatch
    _ = b.rate('5m')
    _ = b.irate('1m')
    _ = b.idelta('30s')
    _ = b.increase('2m')
    _ = b.delta('5m')
    _ = b.changes('10m')
    _ = b.resets('15m')
    _ = b.avg_over_time('5m')
    _ = b.max_over_time('5m')
    _ = b.min_over_time('5m')
    _ = b.sum_over_time('5m')
    _ = b.count_over_time('5m')
    _ = b.stddev_over_time('5m')
    _ = b.stdvar_over_time('5m')
    _ = b.last_over_time('5m')
    _ = b.present_over_time('5m')
    _ = b.deriv('5m')
    _ = b.predict_linear(60, '5m')
    _ = b.mad_over_time('5m')
    _ = b.median_over_time('5m')
    _ = b.mode_over_time('5m')
    _ = b.rate_over_sum('5m')
    _ = b.zscore_over_time('5m')
    _ = b.rollup('avg', '5m')
    _ = b.rollup_rate('5m')

    # holt_winters param bounds
    with pytest.raises(InvalidParameterError):
        b.holt_winters('5m', -0.1, 0.5)
    with pytest.raises(InvalidParameterError):
        b.holt_winters('5m', 0.5, 1.1)


def test_subquery_validation_branching():
    b = FactoryMixin.from_metric('y')
    with pytest.raises(InvalidParameterError):
        b.subquery('')
    with pytest.raises(InvalidParameterError):
        b.subquery('5m', '')


def test_visualize_positions_returns_string():
    b = FactoryMixin.from_metric('cpu').gt(0).sum()
    src = b.build(validate=False)
    s = b.visualize_positions(src)
    assert isinstance(s, str) and 'Source:' in s


def test_validation_strict_true_returns_formatted_errors_and_strict_false_skips():
    # Invalid metric name should produce strict validation errors string
    b_bad = FactoryMixin.from_metric('123')
    msg = b_bad.validate(standard='MetricsQL', strict=True)
    assert isinstance(msg, str) and len(msg) > 0

    # strict=False skips strict AST validation and returns empty string for MetricsQL
    no_err = b_bad.validate(standard='MetricsQL', strict=False)
    assert no_err == ""


def test_validation_catches_validationerror_and_formats(monkeypatch):
    from metricraft._legacy.exceptions import ValidationError
    # Patch validate_ast_node inside the mixin module to raise ValidationError
    import metricraft._legacy.builder.mixins.validation as vmod

    def _boom(*args, **kwargs):
        raise ValidationError(message="boom")

    monkeypatch.setattr(vmod, 'validate_ast_node', _boom)
    b = FactoryMixin.from_metric('cpu')
    out = b.validate(strict=True)
    # Should return formatted string (or str(e) fallback)
    assert isinstance(out, str) and 'boom' in out


def test_datetime_family_and_subquery_success():
    # time-derived family
    t = FactoryMixin.from_time()
    _ = t.day_of_week()
    _ = t.day_of_month()
    _ = t.day_of_year()
    _ = t.hour()
    _ = t.minute()
    _ = t.month()
    _ = t.year()

    # subquery legal path with resolution
    b = FactoryMixin.from_metric('cpu').rate('5m').sum(by=['job'])
    s = b.subquery('10m', '1m')
    assert s.ast_node is not None


def test_range_on_range_with_sign_and_quantile_boundaries_and_rollup():
    # range() called on RangeExpr with a sign state
    r = (-FactoryMixin.from_metric('cpu').range('5m')).range('10m')
    assert r.ast_node is not None

    b = FactoryMixin.from_metric('latency')
    _ = b.quantile_over_time(0.0, '5m')
    _ = b.quantile_over_time(1.0, '5m')

    _ = b.rollup('p95', '5m')


def test_binary_modifier_debug_contains_modifier():
    # Create a binary expression and attach modifiers, then ensure debug text mentions modifier
    expr = (FactoryMixin.from_metric('a').gt(0)).and_(FactoryMixin.from_metric('b').gt(0)).on('job').group_left('env')
    dbg = expr.debug()
    assert 'BINARY_EXPR' in dbg and 'modifier' in dbg


def test_validation_methods_raise_on_none_ast_and_validate_none():
    b = FactoryMixin.from_metric('cpu')
    # manually clear AST to hit InvalidExpressionError branches within ValidationMixin methods
    b._ast_node = None
    from metricraft._legacy.exceptions import VMInvalidExpressionError
    with pytest.raises(VMInvalidExpressionError):
        b.debug()
    with pytest.raises(VMInvalidExpressionError):
        b.to_debug_json()
    with pytest.raises(VMInvalidExpressionError):
        b.debug_positions()
    with pytest.raises(VMInvalidExpressionError):
        b.visualize_positions('up')
    with pytest.raises(VMInvalidExpressionError):
        b.analyze()
    with pytest.raises(VMInvalidExpressionError):
        b.validate()


def test_validation_generic_exception_path(monkeypatch):
    import metricraft._legacy.builder.mixins.validation as vmod

    class _V:
        def visit(self, _):
            raise RuntimeError('oops')

    def _get_visitor():
        return _V()

    monkeypatch.setattr(vmod, 'get_query_visitor', _get_visitor)
    b = FactoryMixin.from_metric('cpu')
    msg = b.validate(strict=False)
    assert msg.startswith('Syntax validation failed: oops')


def test_validation_error_with_formatter(monkeypatch):
    from metricraft._legacy.exceptions import ValidationError
    import metricraft._legacy.builder.mixins.validation as vmod

    class FancyVE(ValidationError):
        def format_error_with_source(self, source):
            return f'FORMATTED({len(source)})'

    def _raise_ve(*args, **kwargs):
        raise FancyVE(message='x')

    monkeypatch.setattr(vmod, 'validate_ast_node', _raise_ve)
    b = FactoryMixin.from_metric('cpu')
    out = b.validate(strict=True)
    assert out.startswith('FORMATTED(')


def test_format_ast_tree_branches():
    # METRIC_SELECTOR
    s = FactoryMixin.from_metric('m').debug()
    assert 'METRIC_SELECTOR' in s
    # NUMBER_LITERAL & STRING_LITERAL & FUNCTION_CALL(no args)
    s2 = FactoryMixin.from_scalar(1).debug()
    assert 'NUMBER_LITERAL' in s2
    s3 = FactoryMixin.from_string('x').debug()
    assert 'STRING_LITERAL' in s3
    s4 = FactoryMixin.from_time().debug()
    assert 'FUNCTION_CALL' in s4 and '[no args]' in s4
    # FUNCTION_CALL(with args) and BINARY_EXPR
    s5 = FactoryMixin.from_metric('m').clamp_min(1).debug()
    assert 'FUNCTION_CALL' in s5 and 'args' in s5
    s6 = FactoryMixin.from_metric('a').add(1).debug()
    assert 'BINARY_EXPR' in s6
    # AGGREGATION_EXPR
    s7 = FactoryMixin.from_metric('a').sum(by=['x']).debug()
    assert 'AGGREGATION_EXPR' in s7 and 'by (x)' in s7
    # UNARY_EXPR
    s8 = (-FactoryMixin.from_metric('u')).debug()
    assert 'UNARY_EXPR' in s8
    # RANGE_EXPR includes DURATION_LITERAL
    s9 = FactoryMixin.from_metric('r').range('5m').debug()
    assert 'RANGE_EXPR' in s9 and 'DURATION_LITERAL' in s9
    # PARENTHESIZED_EXPR
    s10 = FactoryMixin.from_metric('p').add(1).parenthesize().debug()
    assert 'PARENTHESIZED_EXPR' in s10


def test_to_debug_json_and_debug_positions_and_analyze():
    b = FactoryMixin.from_metric('cpu').gt(0).sum()
    js = b.to_debug_json()
    pos = b.debug_positions()
    analysis = b.analyze()
    assert isinstance(js, str) and '{' in js
    assert isinstance(pos, str) and len(pos) > 0
    assert isinstance(analysis, dict)


def test_promql_compat_first_match_priority():
    # Contains both a MetricsQL-only function and a modifier; function should be detected first
    msg = FactoryMixin.from_metric('x').label_set(team='a').sum().keep_metric_names().validate(standard='PromQL')
    # The message includes source snippet; keep_metric_names may appear in context.
    # Assert first match is label_set.
    assert 'label_set' in msg
    first_label_set = msg.lower().find('label_set')
    first_keep = msg.lower().find('keep_metric_names')
    assert first_keep == -1 or first_label_set <= first_keep


def test_format_ast_tree_bool_flag_without_grouping_and_empty_node():
    # BINARY_EXPR (bool) flag (manually construct return_bool=True)
    from metricraft._legacy.tree import BinaryExpr, BinaryOperator, NumberLiteral, MetricSelector
    be = BinaryExpr(MetricSelector('a'), BinaryOperator.GT, NumberLiteral(0), return_bool=True)
    s = FactoryMixin.from_metric('x')._format_ast_tree(be)
    assert '(bool)' in s
    # AGGREGATION_EXPR without branch
    # AGGREGATION_EXPR without branch
    sw = FactoryMixin.from_metric('a').sum().without('job').debug()
    assert 'without (job)' in sw
    # Empty node rendering
    empty = FactoryMixin.from_metric('a')._format_ast_tree(None)
    assert '<empty>' in empty
    # Aggregation with parameter [param: ...]
    sp = FactoryMixin.from_metric('a').topk(3).debug()
    assert '[param:' in sp
    # Unknown node fallback
    class _Dummy:
        node_type = object()
        def __str__(self):
            return 'dummy-node'
    fallback = FactoryMixin.from_metric('a')._format_ast_tree(_Dummy())
    assert 'dummy-node' in fallback


def test_validation_error_formatter_raises_fallback(monkeypatch):
    from metricraft._legacy.exceptions import ValidationError
    import metricraft._legacy.builder.mixins.validation as vmod

    class BadVE(ValidationError):
        def format_error_with_source(self, source):
            raise RuntimeError('nope')

    def _boom(*args, **kwargs):
        raise BadVE(message='bad')

    monkeypatch.setattr(vmod, 'validate_ast_node', _boom)
    b = FactoryMixin.from_metric('cpu')
    out = b.validate(strict=True)
    # After hitting except Exception: pass branch, should return str(e)
    assert out == 'bad'
