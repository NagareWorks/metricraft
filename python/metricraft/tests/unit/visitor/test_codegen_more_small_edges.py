from metricraft._legacy.visitor import QueryToStringVisitor


def test_codegen_weird_node_type_default_visit():
    class X:
        node_type = None
    s = QueryToStringVisitor().visit(X())
    assert s == '<X>'
