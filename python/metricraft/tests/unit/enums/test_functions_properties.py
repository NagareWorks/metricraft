from metricraft._legacy.enums.functions import RangeVectorFunction, MathFunction


def test_range_vector_function_properties():
    assert RangeVectorFunction.RATE.is_standard_promql is True
    assert RangeVectorFunction.QUANTILE_OVER_TIME.is_standard_promql is False
    assert RangeVectorFunction.RATE.requires_duration is True
    assert RangeVectorFunction.QUANTILE_OVER_TIME.requires_extra_params is True
    assert RangeVectorFunction.RATE_OVER_SUM.requires_extra_params is False


def test_math_function_categories():
    assert MathFunction.SIN.is_trigonometric is True
    assert MathFunction.LN.is_trigonometric is False
    assert MathFunction.LN.is_logarithmic is True
    assert MathFunction.SQRT.is_logarithmic is False
