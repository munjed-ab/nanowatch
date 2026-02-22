"""
Web framework middleware for timing HTTP requests end-to-end.

Provides:
  - WsgiMiddleware  : WSGI-compatible (Flask, Django, etc.)
  - AsgiMiddleware  : ASGI-compatible (FastAPI, Starlette, etc.)
  - FlaskExtension  : Flask app.use_nanowatch() shorthand
"""

from typing import Callable, Optional

from ..core.collector import Collector, default_collector
from ..core.timer import Timer
from ..output.formatter import print_record


def _request_label(method: str, path: str) -> str:
    """Build a concise measurement label from HTTP method and path."""
    return f"HTTP {method} {path}"


class WsgiMiddleware:
    """
    WSGI middleware that times each request and records it.

    Compatible with Flask, Django, Bottle, and any WSGI-compliant framework.

    Example (Flask):
        app.wsgi_app = WsgiMiddleware(app.wsgi_app)
    """

    def __init__(self, app, collector: Optional[Collector] = None):
        """
        Wrap a WSGI application.

        Args:
            app: The inner WSGI application callable
            collector: Collector to store records in; defaults to global
        """
        self._app = app
        self._collector = collector or default_collector

    def __call__(self, environ, start_response):
        """Intercept each WSGI request, time it, then pass through."""
        method = environ.get("REQUEST_METHOD", "UNKNOWN")
        path = environ.get("PATH_INFO", "/")
        label = _request_label(method, path)

        timer = Timer(label, context={"method": method, "path": path}).start()
        try:
            return self._app(environ, start_response)
        finally:
            record = timer.stop()
            self._collector.add(record)
            print_record(record)


class AsgiMiddleware:
    """
    ASGI middleware that times each HTTP request and records it.

    Compatible with FastAPI, Starlette, Django Channels, and any ASGI app.

    Example (FastAPI):
        app.add_middleware(AsgiMiddleware)
        # or with custom collector:
        app = AsgiMiddleware(app, collector=my_collector)
    """

    def __init__(self, app, collector: Optional[Collector] = None):
        """
        Wrap an ASGI application.

        Args:
            app: The inner ASGI application callable
            collector: Collector to store records in; defaults to global
        """
        self._app = app
        self._collector = collector or default_collector

    async def __call__(self, scope, receive, send):
        """Intercept each ASGI lifecycle call; time HTTP requests only."""
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        label = _request_label(method, path)

        timer = Timer(label, context={"method": method, "path": path}).start()
        try:
            await self._app(scope, receive, send)
        finally:
            record = timer.stop()
            self._collector.add(record)
            print_record(record)


def flask_extension(app, collector: Optional[Collector] = None):
    """
    Convenience function to attach WSGI timing middleware to a Flask app.

    Args:
        app: Flask application instance
        collector: Optional custom collector

    Returns:
        The same app instance (mutated in place)
    """
    app.wsgi_app = WsgiMiddleware(app.wsgi_app, collector=collector)
    return app