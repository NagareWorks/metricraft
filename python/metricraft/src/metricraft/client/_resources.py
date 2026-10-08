"""Ownership and release of the HTTP transports held by one client."""
import logging


_logger = logging.getLogger(__name__)


def _close(transport) -> None:
    try:
        close = getattr(transport, "close", None)
        if callable(close):
            close()
    except Exception:
        _logger.debug("Exception while closing HTTP transport", exc_info=True)


class TransportResources:
    """Concrete transport owner, independent of the DatabaseClient lifetime.

    A finalizer may retain this object without retaining the client itself.
    Async-only transports require explicit aclose() or an async context manager.
    """

    __slots__ = ("sync", "async_", "closed")

    def __init__(self):
        self.sync = None
        self.async_ = None
        self.closed = False

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        sync = getattr(self, "sync", None)
        async_ = getattr(self, "async_", None)
        if async_ is not sync:
            _close(async_)
        _close(sync)

    async def aclose(self) -> None:
        if self.closed:
            return
        self.closed = True
        sync = getattr(self, "sync", None)
        async_ = getattr(self, "async_", None)
        async_closed = False
        try:
            aclose = getattr(async_, "aclose", None)
            if callable(aclose):
                await aclose()
                async_closed = True
        except Exception:
            _logger.debug("Exception while asynchronously closing HTTP transport", exc_info=True)
        finally:
            if not async_closed:
                _close(async_)
            if sync is not async_:
                _close(sync)
