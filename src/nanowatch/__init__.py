"""
nanowatch - High-precision Python performance measurement toolkit.

Provides multiple interfaces to measure execution time at any granularity:
  - @watch               : function/method decorator
  - watch_block()        : context manager for code blocks
  - watch_call()         : time a single call without decorating
  - WatchedMixin         : auto-instrument all methods of a class
  - WsgiMiddleware  : WSGI-compatible (Flask, Django, etc.)
  - AsgiMiddleware  : ASGI-compatible (FastAPI, Starlette, etc.)
  - FlaskExtension  : Flask app.use_nanowatch() shorthand
  - LineProfiler         : checkpoint-based line-level profiling
  - summary()            : print a full report to stdout
  - save()               : persist all results to a JSON file
  - collector            : access the default global Collector

All measurements use time.perf_counter_ns for nanosecond precision.
"""

from .core.collector import Collector, default_collector
from .core.timer import Timer, TimingRecord

from .interfaces.decorators import watch, watch_block, watch_call
from .interfaces.mixin import WatchedMixin
from .interfaces.middleware import WsgiMiddleware, AsgiMiddleware, flask_extension
from .interfaces.line_profiler import LineProfiler

from .output.formatter import print_summary, save_to_file


def summary() -> None:
    """Print a formatted performance summary from the global collector."""
    print_summary(default_collector)


def save(path: str) -> None:
    """
    Save all recorded measurements to a JSON file.

    Args:
        path: Output file path (e.g. "perf_results.json")
    """
    save_to_file(default_collector, path)


def reset() -> None:
    """Clear all measurements from the global collector."""
    default_collector.clear()


collector = default_collector

__all__ = [
    "watch",
    "watch_block",
    "watch_call",
    "WatchedMixin",
    "WsgiMiddleware",
    "AsgiMiddleware",
    "flask_extension",
    "LineProfiler",
    "summary",
    "save",
    "reset",
    "collector",
    "Collector",
    "Timer",
    "TimingRecord",
]