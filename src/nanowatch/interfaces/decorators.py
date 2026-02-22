"""
Function and method timing interfaces: decorator and context manager.

Usage:
    @watch                          # uses default name (function name)
    def my_function(): ...

    @watch("custom label")          # uses custom name
    def my_function(): ...

    with watch_block("db query"):   # inline block timing
        result = db.query(...)
"""

import asyncio
import functools
from contextlib import contextmanager
from typing import Callable, Optional

from ..core.collector import Collector, default_collector
from ..core.timer import Timer
from ..output.formatter import print_record


def _make_wrapper(fn: Callable, name: str, collector: Collector) -> Callable:
    """Wrap a callable to time each invocation and record the result."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        timer = Timer(name).start()
        try:
            return fn(*args, **kwargs)
        finally:
            record = timer.stop()
            collector.add(record)
            print_record(record)

    return wrapper


def _make_async_wrapper(fn: Callable, name: str, collector: Collector) -> Callable:
    """Wrap an async callable to time each invocation."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        timer = Timer(name).start()
        try:
            return await fn(*args, **kwargs)
        finally:
            record = timer.stop()
            collector.add(record)
            print_record(record)

    return wrapper


def _build_decorator(label: Optional[str], collector: Collector) -> Callable:
    """Return a decorator that times the given function with the resolved label."""

    def decorator(fn: Callable) -> Callable:
        name = label or fn.__qualname__
        if asyncio.iscoroutinefunction(fn):
            return _make_async_wrapper(fn, name, collector)
        return _make_wrapper(fn, name, collector)

    return decorator


def watch(arg=None, *, name: Optional[str] = None, collector: Optional[Collector] = None):
    """
    Decorator that times a function or method on every call.

    Supported usage patterns:
        @watch
        @watch("custom name")
        @watch(name="custom name")
        @watch(collector=my_collector)
        @watch("name", collector=my_collector)

    Args:
        arg: Either the decorated function (bare @watch) or a string label
        name: Keyword-only custom label
        collector: Collector to store records; defaults to global default_collector
    """
    active_collector = collector or default_collector

    if callable(arg):
        return _build_decorator(name, active_collector)(arg)

    if isinstance(arg, str):
        return _build_decorator(arg, active_collector)

    return _build_decorator(name, active_collector)


@contextmanager
def watch_block(name: str, collector: Optional[Collector] = None):
    """
    Context manager for timing an inline block of code.

    Args:
        name: Label for this measurement
        collector: Custom collector; defaults to the global default_collector

    Example:
        with watch_block("parse json"):
            data = json.loads(raw)
    """
    active_collector = collector or default_collector
    timer = Timer(name).start()
    try:
        yield timer
    finally:
        record = timer.stop()
        active_collector.add(record)
        print_record(record)


def watch_call(fn: Callable, *args, name: Optional[str] = None,
               collector: Optional[Collector] = None, **kwargs):
    """
    Time a single function call without decorating the function.

    Useful when you don't control the source of the function.

    Args:
        fn: The callable to time
        *args: Positional arguments forwarded to fn
        name: Custom label; defaults to fn's qualified name
        collector: Custom collector; defaults to the global default_collector
        **kwargs: Keyword arguments forwarded to fn

    Returns:
        The return value of fn(*args, **kwargs)
    """
    active_collector = collector or default_collector
    label = name or getattr(fn, "__qualname__", repr(fn))
    timer = Timer(label).start()
    try:
        return fn(*args, **kwargs)
    finally:
        record = timer.stop()
        active_collector.add(record)
        print_record(record)
