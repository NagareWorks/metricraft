import pytest


def test_native_builder_rejects_python_visitor_override():
    from metricraft import QueryBuilder

    query = QueryBuilder.from_metric("m")
    with pytest.raises(TypeError, match="visitor"):
        query.build(visitor=object())
    assert query.build() == "m"
