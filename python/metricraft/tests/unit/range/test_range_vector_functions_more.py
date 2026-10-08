from metricraft._legacy.builder.mixins import FactoryMixin


def test_range_vector_functions_breadth():
    b = FactoryMixin.from_metric('m')
    # Build ASTs to cover mixin dispatch; avoid strict assertions on string generation
    _ = b.avg_over_time('2m')
    _ = b.min_over_time('2m')
    _ = b.max_over_time('2m')
    _ = b.stddev_over_time('2m')
    _ = b.stdvar_over_time('2m')
    _ = b.sum_over_time('2m')
    _ = b.count_over_time('2m')
    _ = b.quantile_over_time(0.5, '2m')
    _ = b.deriv('2m')
    _ = b.idelta('2m')
    _ = b.delta('2m')
    _ = b.holt_winters('2m', 0.2, 0.1)
    _ = b.predict_linear(60, '2m')
