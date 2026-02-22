"""
WatchedMixin: add to any class to automatically time all its public methods.

Usage:
    class MyService(WatchedMixin):
        def do_work(self): ...       # timed automatically
        def _private(self): ...      # skipped (underscore prefix)

    class MyService(WatchedMixin, prefix="MyService"):
        ...  # label will be "MyService.do_work" instead of class qualname
"""

import functools
import inspect
from typing import Optional

from ..core.collector import Collector, default_collector
from ..core.timer import Timer
from ..output.formatter import print_record

DUNDER_METHOD = "__"


def _is_measurable_method(name: str, value) -> bool:
    """Return True if the attribute should be instrumented."""
    is_private = name.startswith("_")
    is_callable = callable(value)
    return is_callable and not is_private


def _wrap_method(method, label: str, collector: Collector):
    """Return a timed version of the given method."""
    if inspect.iscoroutinefunction(method):
        return _wrap_async_method(method, label, collector)
    return _wrap_sync_method(method, label, collector)


def _wrap_sync_method(method, label: str, collector: Collector):
    """Wrap a synchronous method with timing logic."""

    @functools.wraps(method)
    def timed(*args, **kwargs):
        timer = Timer(label).start()
        try:
            return method(*args, **kwargs)
        finally:
            record = timer.stop()
            collector.add(record)
            print_record(record)

    return timed


def _wrap_async_method(method, label: str, collector: Collector):
    """Wrap an async method with timing logic."""

    @functools.wraps(method)
    async def timed(*args, **kwargs):
        timer = Timer(label).start()
        try:
            return await method(*args, **kwargs)
        finally:
            record = timer.stop()
            collector.add(record)
            print_record(record)

    return timed


class WatchedMeta(type):
    """
    Metaclass that instruments all public methods at class creation time.

    Avoids runtime overhead per-call by wrapping once during class definition.
    Respects a `_watch_collector` and `_watch_prefix` class attribute for DI.
    """

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        collector: Collector = namespace.get("_watch_collector", default_collector)
        prefix: str = namespace.get("_watch_prefix", name)

        for attr_name, attr_value in list(namespace.items()):
            if not _is_measurable_method(attr_name, attr_value):
                continue
            label = f"{prefix}.{attr_name}"
            setattr(cls, attr_name, _wrap_method(attr_value, label, collector))

        return cls


class WatchedMixin(metaclass=WatchedMeta):
    """
    Mixin that auto-times every public method of the subclass.

    Configure via class attributes:
        _watch_collector : Collector instance to use (default: global)
        _watch_prefix    : Label prefix for measurements (default: class name)

    Example:
        class UserService(WatchedMixin):
            _watch_prefix = "UserService"
            _watch_collector = my_collector

            def fetch_user(self, user_id): ...
            def save_user(self, user): ...
    """

    _watch_collector: Collector = default_collector
    _watch_prefix: str = ""