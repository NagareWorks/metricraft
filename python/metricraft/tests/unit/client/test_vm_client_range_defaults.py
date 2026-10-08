import time as _time
from metricraft import DatabaseClient


def test_query_range_defaults(monkeypatch):
    client = DatabaseClient()

    # Fix current time
    monkeypatch.setattr('metricraft.client._time.time', type('T', (), {'time': staticmethod(lambda: 1700003600)})())

    calls = {}
    class Dummy:
        def get(self, url, params=None):
            calls['url'] = url
            calls['params'] = params or {}
            return {'status': 'success', 'data': {'resultType': 'matrix', 'result': []}}
    monkeypatch.setattr(client, 'client', Dummy())

    # No start/end/step provided -> use defaults
    res = client.query_range('up')
    assert res.is_success
    assert calls['url'].endswith('/api/v1/query_range')
    # step default comes from client.default_step
    assert 'step' in calls['params'] and calls['params']['step']
    # start computed = end-3600 and normalized to string
    assert int(calls['params']['end']) == 1700003600
    assert int(calls['params']['start']) == 1700003600 - 3600
