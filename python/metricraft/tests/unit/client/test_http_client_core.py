"""
Core-level tests for HTTP client utilities.

Covers SyncHTTPClient and AsyncHTTPClient behavior, focusing on
framework exceptions and parameter handling. This intentionally avoids
any provider-specific logic.
"""

import asyncio
import json
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch
from urllib.error import HTTPError as URLLibHTTPError, URLError
from urllib.request import Request

import pytest

from metricraft.client.http_client import (
    SyncHTTPClient,
    AsyncHTTPClient,
    mask_sensitive_headers,
    _prepare_params,
)
from metricraft.exceptions import MCHTTPError, TimeoutError, ConnectionError


class _ImmediateLoop:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def run_in_executor(self, executor, func):
        future = self._loop.create_future()
        try:
            result = func()
        except Exception as exc:  # pragma: no cover - exercised via tests
            future.set_exception(exc)
        else:
            future.set_result(result)
        return future


class TestSyncHTTPClient:
    def setup_method(self):
        self.client = SyncHTTPClient(timeout=1)

    @patch("metricraft.client.http_client.urlopen")
    def test_get_success(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        res = self.client.get("http://example/api", {"a": 1, "b": None})
        assert res == {"ok": True}
        # ensure that None param was filtered
        req = mock_urlopen.call_args[0][0]
        assert "?a=1" in req.full_url and "b=" not in req.full_url

        # No params path
        _ = self.client.get("http://example/api2")

    @patch("metricraft.client.http_client.urlopen")
    def test_get_http_error_json_body(self, mock_urlopen):
        # emulate HTTPError with JSON body
        body = b"{\"error\": \"bad\"}"
        fp = Mock()
        fp.read.return_value = body
        err = URLLibHTTPError(url="http://x", code=400, msg="Bad", hdrs={}, fp=fp)
        err.read = Mock(return_value=body)
        mock_urlopen.side_effect = err

        with pytest.raises(MCHTTPError) as e:
            self.client.get("http://example/api")
        assert e.value.status_code == 400
        assert e.value.response_data == {"error": "bad"}

    @patch("metricraft.client.http_client.urlopen")
    def test_get_timeout_and_connection(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("timed out")
        with pytest.raises(TimeoutError):
            self.client.get("http://example/api")

        mock_urlopen.side_effect = URLError("connection refused")
        with pytest.raises(ConnectionError):
            self.client.get("http://example/api")

        # OSError with timeout phrase
        mock_urlopen.side_effect = OSError("Connection timed out")
        with pytest.raises(TimeoutError):
            self.client.get("http://example/api")

    @patch("metricraft.client.http_client.urlopen")
    def test_post_success_and_content_type(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        # JSON body
        res = self.client.post("http://example/post", data={"k": "v"})
        assert res == {"ok": True}
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/json"

        # Raw text body
        res = self.client.post("http://example/post", data="raw")
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "text/plain"

        # With params (ensure URL has query)
        _ = self.client.post("http://example/post", data={}, params={"x": 1})
        req = mock_urlopen.call_args[0][0]
        assert "?x=1" in req.full_url

    @patch("metricraft.client.http_client.urlopen")
    def test_request_handles_explicit_content_type_and_none_body(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        res = self.client.request(
            "DELETE",
            "http://example/delete",
            data=None,
            content_type="application/custom",
        )
        assert res == {"ok": True}
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/custom"

    @patch("metricraft.client.http_client.urlopen")
    def test_request_bytes_and_string_payloads(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        self.client.request("PUT", "http://example/bytes", data=b"payload")
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/octet-stream"

        self.client.request("PATCH", "http://example/text", data="hello")
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "text/plain"

    @patch("metricraft.client.http_client.urlopen")
    def test_request_respects_explicit_content_type_override(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        self.client.request(
            "POST",
            "http://example/custom",
            data={"x": 1},
            content_type="application/x-custom",
        )
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/x-custom"

    def test_request_rejects_unsupported_payload(self):
        with pytest.raises(TypeError):
            self.client.request("POST", "http://example/invalid", data=object())

    @patch("metricraft.client.http_client.urlopen")
    def test_request_custom_method_and_body_types(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"updated": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        res = self.client.request(
            "PUT",
            "http://example/resource",
            data=b"payload",
            headers={"X-Test": "1"},
            content_type="application/octet-stream",
        )

        assert res == {"updated": True}
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "PUT"
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/octet-stream"
        assert headers["X-Test"] == "1"

    @patch("metricraft.client.http_client.urlopen")
    def test_post_http_error_invalid_json(self, mock_urlopen):
        fp = Mock()
        fp.read.return_value = b"not json"
        err = URLLibHTTPError(url="http://x", code=500, msg="ERR", hdrs={}, fp=fp)
        err.read = Mock(return_value=b"not json")
        mock_urlopen.side_effect = err

        with pytest.raises(MCHTTPError) as e:
            self.client.post("http://example/post", data={})
        assert e.value.status_code == 500
        assert e.value.response_data == {}

    @patch("metricraft.client.http_client.urlopen")
    def test_post_timeout_and_connection(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("timed out")
        with pytest.raises(TimeoutError):
            self.client.post("http://example/post", data={})

        mock_urlopen.side_effect = OSError("refused")
        with pytest.raises(ConnectionError):
            self.client.post("http://example/post", data={})

    @patch("metricraft.client.http_client.time.sleep")
    def test_retry_on_transient_network_error(self, sleep_mock):
        attempts = {"count": 0}

        def opener(request, timeout=None):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise URLError("timed out")

            response = Mock()
            response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=None)
            return response

        client = SyncHTTPClient(
            timeout=1,
            opener=opener,
            retries=3,
            backoff_factor=0.1,
        )

        result = client.get("http://example/retry")
        assert result == {"ok": True}
        assert attempts["count"] == 3

        delays = [call.args[0] for call in sleep_mock.call_args_list]
        assert delays == pytest.approx([0.1, 0.2])

    @patch("metricraft.client.http_client.time.sleep")
    def test_retry_on_retryable_status_code(self, sleep_mock):
        attempts = {"count": 0}

        def opener(request, timeout=None):
            attempts["count"] += 1
            if attempts["count"] == 1:
                body = b"{\"error\": \"busy\"}"
                err = URLLibHTTPError(
                    url=request.full_url,
                    code=503,
                    msg="busy",
                    hdrs={},
                    fp=BytesIO(body),
                )
                err.read = Mock(return_value=body)
                raise err

            response = Mock()
            response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=None)
            return response

        client = SyncHTTPClient(timeout=1, opener=opener, retries=2)

        result = client.get("http://example/service")
        assert result == {"ok": True}
        assert attempts["count"] == 2

        delays = [call.args[0] for call in sleep_mock.call_args_list]
        assert delays == pytest.approx([0.5])

    @patch("metricraft.client.http_client.time.sleep")
    def test_does_not_retry_on_non_retryable_status_code(self, sleep_mock):
        def opener(request, timeout=None):
            body = b"{\"error\": \"bad\"}"
            err = URLLibHTTPError(
                url=request.full_url,
                code=400,
                msg="bad",
                hdrs={},
                fp=BytesIO(body),
            )
            err.read = Mock(return_value=body)
            raise err

        client = SyncHTTPClient(timeout=1, opener=opener, retries=4)

        with pytest.raises(MCHTTPError) as exc:
            client.post("http://example/nonretry", data={})

        assert exc.value.status_code == 400
        sleep_mock.assert_not_called()

    @patch("metricraft.client.http_client.time.sleep")
    def test_retry_respects_method_whitelist(self, sleep_mock):
        attempts = {"count": 0}

        def opener(request, timeout=None):
            attempts["count"] += 1
            raise URLError("connection reset")

        client = SyncHTTPClient(
            timeout=1,
            opener=opener,
            retries=5,
            retry_methods={"GET"},
        )

        with pytest.raises(ConnectionError):
            client.post("http://example/whitelist", data={})

        assert attempts["count"] == 1
        sleep_mock.assert_not_called()

    def test_prepare_params_helper(self):
        out = _prepare_params({"a": None, "b": [1, 2], "c": 3})
        assert out == {"b": ["1", "2"], "c": "3"}

    @patch("metricraft.client.http_client.urlopen")
    def test_match_selectors_are_repeated_query_parameters(self, mock_urlopen):
        from urllib.parse import parse_qs, urlsplit
        response = Mock()
        response.read.return_value = b'{"status":"success","data":[]}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = response
        selectors = ['up{job="api,worker"}', 'down{note="a&b"}']
        client = SyncHTTPClient(timeout=1)
        try:
            client.get("http://example/api/v1/series", {"match[]": selectors})
        finally:
            client.close()
        request = mock_urlopen.call_args[0][0]
        assert parse_qs(urlsplit(request.full_url).query)["match[]"] == selectors

    @patch("metricraft.client.http_client.urlopen")
    def test_default_headers_merge(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        client = SyncHTTPClient(timeout=1, default_headers={"Authorization": "secret"})
        client.get(
            "http://example/auth",
            headers={"Authorization": "override", "X-Test": 123},
        )
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Authorization"] == "override"
        assert headers["X-Test"] == "123"

    @patch("metricraft.client.http_client.urlopen")
    def test_get_appends_params_to_existing_query(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        self.client.get("http://example/api?existing=1", params={"next": 2})
        req = mock_urlopen.call_args[0][0]
        assert "existing=1" in req.full_url
        assert "next=2" in req.full_url
        assert "?" in req.full_url and "&" in req.full_url

    @patch.object(SyncHTTPClient, "request")
    def test_extra_http_verbs_delegate_to_request(self, mrequest):
        mrequest.return_value = {"ok": True}

        self.client.put("http://example/put", data={"a": 1}, content_type="application/json")
        self.client.patch("http://example/patch", data="body")
        self.client.delete("http://example/delete", params={"q": 1})
        self.client.head("http://example/head")
        self.client.options("http://example/options", headers={"X": "1"})

        methods = [call.args[0] for call in mrequest.call_args_list]
        assert methods == ["PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

    @patch("metricraft.client.http_client.urlopen")
    def test_prepare_request_hook(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        def hook(request):
            request.add_header("X-Hook", "1")

        client = SyncHTTPClient(timeout=1, prepare_request=hook)
        client.get("http://example/hook")
        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["X-Hook"] == "1"

    @patch("metricraft.client.http_client.urlopen")
    def test_prepare_request_hook_can_replace_request_and_canonicalize(self, mock_urlopen):
        mock_resp = Mock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_resp

        def hook(request):
            replacement = Request(request.full_url, data=request.data, method=request.get_method())
            replacement.add_header("content-type", "application/custom")
            replacement.unredirected_hdrs["x-test"] = "value"
            return replacement

        client = SyncHTTPClient(timeout=1, prepare_request=hook)
        client.get("http://example/replace")

        req = mock_urlopen.call_args[0][0]
        headers = dict(req.header_items())
        assert headers["Content-type"] == "application/custom"
        assert "X-Test" in req.unredirected_hdrs

    def test_timeout_tuple_normalization(self):
        client = SyncHTTPClient(timeout=(5, 10))
        assert client.connect_timeout == 5
        assert client.timeout == 10
        assert client._resolve_timeouts(None) == (5, 10)
        assert client._resolve_timeouts(2) == (2, 2)

    def test_timeout_single_value_sequence(self):
        client = SyncHTTPClient(timeout=[7])
        assert client.connect_timeout == 7
        assert client.timeout == 7

    def test_timeout_empty_sequence_raises(self):
        with pytest.raises(ValueError):
            SyncHTTPClient(timeout=())

    def test_timeout_negative_value_raises(self):
        with pytest.raises(ValueError):
            SyncHTTPClient(timeout=-1)

    def test_mask_sensitive_headers_helper(self):
        headers = {
            "Authorization": "Bearer secret",
            "X-TOKEN": "abc",
            "Content-Type": "application/json",
        }
        masked = mask_sensitive_headers(headers)
        assert masked["Authorization"] == "******"
        assert masked["X-TOKEN"] == "******"
        assert masked["Content-Type"] == "application/json"


class TestAsyncHTTPClient:
    def setup_method(self):
        self.client = AsyncHTTPClient(timeout=1)

    @patch.object(SyncHTTPClient, "request")
    @pytest.mark.asyncio
    async def test_async_get_success(self, mget):
        mget.return_value = {"ok": True}
        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            res = await self.client.get("http://example/api", {"q": "1"})
        assert res == {"ok": True}
        method, url = mget.call_args[0][:2]
        assert method == "GET"
        assert url == "http://example/api"
        mget.assert_called_once()

    @patch.object(SyncHTTPClient, "request")
    @pytest.mark.asyncio
    async def test_async_post_success(self, mpost):
        mpost.return_value = {"ok": True}
        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            res = await self.client.post("http://example/post", data={"a": 1})
        assert res == {"ok": True}
        method, url = mpost.call_args[0][:2]
        assert method == "POST"
        assert url == "http://example/post"
        mpost.assert_called_once()

    @patch.object(SyncHTTPClient, "request")
    @pytest.mark.asyncio
    async def test_async_get_error_mapping(self, mget):
        mget.side_effect = Exception("timeout occurred")
        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(TimeoutError):
                await self.client.get("http://x")

        mget.side_effect = MCHTTPError(400, "bad", {})
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(MCHTTPError):
                await self.client.get("http://x")

        mget.side_effect = Exception("weird")
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(ConnectionError):
                await self.client.get("http://x")

    @patch.object(SyncHTTPClient, "request")
    @pytest.mark.asyncio
    async def test_async_post_error_mapping(self, mpost):
        mpost.side_effect = Exception("timeout occurred")
        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(TimeoutError):
                await self.client.post("http://x", data={})

        mpost.side_effect = MCHTTPError(500, "bad", {})
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(MCHTTPError):
                await self.client.post("http://x", data={})

        mpost.side_effect = Exception("oops")
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(ConnectionError):
                await self.client.post("http://x", data={})

    @pytest.mark.asyncio
    async def test_async_extra_http_verbs_delegate_to_request(self):
        client = AsyncHTTPClient(timeout=1)

        with patch.object(AsyncHTTPClient, "request", new_callable=AsyncMock) as mrequest:
            mrequest.return_value = {"ok": True}

            await client.put("http://example/put")
            await client.patch("http://example/patch")
            await client.delete("http://example/delete")
            await client.head("http://example/head")
            await client.options("http://example/options")

            methods = [call.args[0] for call in mrequest.call_args_list]
            assert methods == ["PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

    @pytest.mark.asyncio
    async def test_async_request_falls_back_to_get_and_post(self):
        class LegacyClient:
            def __init__(self):
                self.calls = []

            def get(self, url, params=None, headers=None, timeout=None):
                self.calls.append(("GET", url, params, headers, timeout))
                return {"method": "GET"}

            def post(self, url, data=None, params=None, headers=None, timeout=None):
                self.calls.append(("POST", url, params, headers, timeout))
                return {"method": "POST"}

        legacy = LegacyClient()
        async_client = AsyncHTTPClient(sync_client=legacy)

        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())
        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            res_get = await async_client.request("GET", "http://example/get", params={"a": 1})
        assert res_get == {"method": "GET"}
        assert legacy.calls[0][0] == "GET"

        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            res_post = await async_client.request("POST", "http://example/post", data={"x": 1})
        assert res_post == {"method": "POST"}
        assert legacy.calls[1][0] == "POST"

    @pytest.mark.asyncio
    async def test_async_request_with_incompatible_client_raises_connection_error(self):
        class BadClient:
            pass

        client = AsyncHTTPClient(sync_client=BadClient())
        immediate_loop = _ImmediateLoop(asyncio.get_running_loop())

        with patch.object(AsyncHTTPClient, "_get_event_loop", return_value=immediate_loop):
            with pytest.raises(ConnectionError):
                await client.request("PATCH", "http://example/bad")

    def test_async_client_del(self):
        # Explicitly invoke __del__ to cover shutdown branch
        c = AsyncHTTPClient(timeout=1)
        c.__del__()
