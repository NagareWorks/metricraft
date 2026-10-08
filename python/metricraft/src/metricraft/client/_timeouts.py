"""urllib handlers that switch from the connection budget to the read budget."""
from http.client import HTTPConnection, HTTPSConnection
from urllib.request import HTTPHandler, HTTPSHandler, build_opener


def phased_opener(read_timeout):
    class HTTP(HTTPConnection):
        def connect(self):
            super().connect()
            self.sock.settimeout(read_timeout)

    class HTTPS(HTTPSConnection):
        def connect(self):
            super().connect()
            self.sock.settimeout(read_timeout)

    class PlainHandler(HTTPHandler):
        def http_open(self, request):
            return self.do_open(HTTP, request)

    class SecureHandler(HTTPSHandler):
        def https_open(self, request):
            return self.do_open(HTTPS, request, context=self._context)

    return build_opener(PlainHandler(), SecureHandler()).open
