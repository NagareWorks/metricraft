from metricraft import DatabaseClient


def test_vm_client_health_exception_returns_false(monkeypatch):
    c = DatabaseClient()
    # Make underlying HTTP client raise to trigger except path
    class Boom:
        def get(self, *a, **k):
            raise RuntimeError("boom")
    monkeypatch = monkeypatch  # noqa: F841 just to keep reference
    # Patch low-level client used in health()
    object.__setattr__(c, 'client', Boom())
    assert c.health() is False
