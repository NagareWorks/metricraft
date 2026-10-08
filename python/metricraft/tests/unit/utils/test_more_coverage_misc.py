import pytest

from metricraft._legacy.ast import Position
from metricraft._legacy.builder.mixins import FactoryMixin
from metricraft._legacy.builder.impl.base import MetricsBuilder
from metricraft._legacy.builder.utils import templates as T
from metricraft._legacy.tree import NumberLiteral, StringLiteral
from metricraft._legacy.enums import AggregationOperator, BinaryOperator
from metricraft._legacy.exceptions import VMInvalidExpressionError, VMValidationError


def test_transformation_datetime_family_and_sort_desc():
    b = FactoryMixin.from_metric('cpu').timestamp()
    # date/time functions
    _ = b.day_of_week().day_of_month().day_of_year().hour().minute().month().year()
    # dedup and sort combos
    _ = b.dedup().sort().sort_desc()


def test_aggregation_family_and_param_validations():
    b = FactoryMixin.from_metric('cpu')
    # promql standard + metricsql extensions
    _ = b.stddev(); _ = b.stdvar(); _ = b.count(); _ = b.count_values('ver')
    _ = b.group(); _ = b.any(); _ = b.median(); _ = b.mode(); _ = b.mad()
    # topk/bottomk/quantile valid edges
    _ = b.topk(1); _ = b.bottomk(2); _ = b.quantile(0.0); _ = b.quantile(1.0)
    # histogram_quantile with both float and builder q
    _ = b.histogram_quantile(0.5)
    qbuilder = FactoryMixin.from_scalar(0.9)
    _ = b.histogram_quantile(qbuilder)
    # invalid k
    with pytest.raises(Exception):
        b.topk(0)
    # invalid quantile
    with pytest.raises(Exception):
        b.quantile(1.5)


def test_sign_mixin_positive_negative_magic():
    b = FactoryMixin.from_metric('m')
    # + and - magic
    bp = +b
    assert isinstance(bp, MetricsBuilder)
    bn = -b
    # double negative becomes positive state
    bnn = (-bn)
    assert isinstance(bnn, MetricsBuilder)


def test_time_range_at_special_functions():
    b = FactoryMixin.from_metric('cpu')
    _ = b.at('start()')
    _ = b.at('end()')


def test_templates_create_aggregation_param_node_and_convert_to_ast_node_string_metric():
    b = FactoryMixin.from_metric('x')
    n = NumberLiteral(3)
    # direct param as AST node
    out = T.create_aggregation_function(b, AggregationOperator.TOPK, param=n)
    assert out.ast_node is not None
    # convert_to_ast_node with metric string
    node = T.convert_to_ast_node('mymetric')
    assert getattr(node, 'metric_name', None) == 'mymetric'


def test_invalid_expression_legacy_position_and_validation_error_constructors():
    pos = Position(offset=1, length=2, index_in_parent=0)
    err = VMInvalidExpressionError('op', position=pos)
    assert 'InvalidExpression' in str(err)
    # VMValidationError message-based
    ve1 = VMValidationError(message='bad', context='ctx')
    assert 'bad' in str(ve1)
    # legacy
    ve2 = VMValidationError(validation_type='syntax', issue='oops', standard='PromQL')
    assert 'syntax' in str(ve2)


def test_validation_mixin_exception_paths(monkeypatch):
    b = FactoryMixin.from_metric('cpu').where_eq('job', 'api')

    # Path 1: validate_ast_node returns errors list -> formatted string
    def fake_validate(node, root):
        return [VMValidationError(message='E', ast_node=node, root_node=root)]
    # Patch the alias used inside ValidationMixin
    monkeypatch.setattr('metricraft._legacy.builder.mixins.validation.validate_ast_node', fake_validate)
    msg = b.validate(standard='MetricsQL', strict=True)
    assert isinstance(msg, str) and msg

    # Path 2: validate_ast_node raises ValidationError -> except path
    def raise_validate(node, root):
        raise VMValidationError(message='X', ast_node=node, root_node=root)
    monkeypatch.setattr('metricraft._legacy.builder.mixins.validation.validate_ast_node', raise_validate)
    msg2 = b.validate(standard='MetricsQL', strict=True)
    assert isinstance(msg2, str) and 'X' in msg2

    # Path 3: get_query_visitor().visit raises generic Exception -> Syntax validation failed
    class Boom(Exception):
        pass
    def boom():
        class V:  # duck-typed visitor with visit method
            def visit(self, node):
                raise Boom('boom')
        return V()
    # Patch the alias imported into ValidationMixin
    monkeypatch.setattr('metricraft._legacy.builder.mixins.validation.get_query_visitor', boom)
    msg3 = b.validate(standard='MetricsQL', strict=True)
    assert isinstance(msg3, str) and 'Syntax validation failed' in msg3


def test_ast_debugger_properties_matching_and_no_source_visualize():
    a = FactoryMixin.from_metric('a')
    b = FactoryMixin.from_metric('b')
    expr = a.or_(b)
    # force matching property branch exposure
    node = expr.ast_node
    assert node is not None
    setattr(node, 'matching', True)
    dbg_text = expr.debug()
    assert isinstance(dbg_text, str)
    # visualize without source -> should return positions map string or no info
    vis = expr.visualize_positions(None)  # type: ignore[arg-type]
    assert isinstance(vis, str)


def test_validation_promql_compatibility_for_metricsql_only_features():
    # MetricsQL-only modifier keep_metric_names
    b1 = FactoryMixin.from_metric('cpu').keep_metric_names()
    msg1 = b1.validate(standard='PromQL', strict=False)
    assert isinstance(msg1, str) and 'PromQL compatibility error' in msg1

    # MetricsQL-only functions union/limitk/outliersk
    b2 = FactoryMixin.from_metric('a').union(FactoryMixin.from_metric('b'))
    msg2 = b2.validate(standard='PromQL', strict=False)
    assert 'PromQL compatibility error' in msg2

    b3 = FactoryMixin.from_metric('cpu').limitk(5)
    assert 'PromQL compatibility error' in b3.validate(standard='PromQL', strict=False)

    b4 = FactoryMixin.from_metric('cpu').outliersk(3)
    assert 'PromQL compatibility error' in b4.validate(standard='PromQL', strict=False)


def test_transformation_subquery_success_paths():
    src = FactoryMixin.from_metric('cpu')
    # with resolution
    s1 = src.subquery('10m', '1m')
    assert isinstance(s1, MetricsBuilder) and s1.ast_node is not None
    # without resolution
    s2 = src.subquery('5m')
    assert isinstance(s2, MetricsBuilder) and s2.ast_node is not None


def test_metricsbuilder_build_validate_and_custom_visitor(monkeypatch):
    b = FactoryMixin.from_metric('m').where_eq('job', 'api')

    # validate=False returns generated string
    s = b.build(validate=False)
    assert isinstance(s, str) and 'm' in s

    # validate=True raising first validation error
    def fake_validate(node, root):
        return [VMValidationError(message='Err', ast_node=node, root_node=root)]
    monkeypatch.setattr('metricraft._legacy.tree.utils.validation.validate_ast_node', fake_validate)
    with pytest.raises(VMValidationError):
        _ = b.build(validate=True)

    # custom visitor
    class V:
        def visit(self, node):
            return 'OK'
    out = b.build(validate=False, visitor=V())
    assert out == 'OK'


def test_sign_mixin_errors_on_empty_builder():
    empty = MetricsBuilder()
    with pytest.raises(VMInvalidExpressionError):
        _ = (+empty)
    with pytest.raises(VMInvalidExpressionError):
        _ = (-empty)
