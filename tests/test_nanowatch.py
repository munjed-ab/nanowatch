"""
Test suite for nanowatch.

Covers: Timer precision, Collector aggregation, all interfaces,
decorator sync/async, mixin, middleware, line profiler, output.
"""

import asyncio
import json
import os
import time
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import nanowatch
from nanowatch.core.timer import Timer, TimingRecord
from nanowatch.core.collector import Collector
from nanowatch.interfaces.decorators import watch, watch_block, watch_call
from nanowatch.interfaces.mixin import WatchedMixin
from nanowatch.interfaces.middleware import WsgiMiddleware, AsgiMiddleware
from nanowatch.interfaces.line_profiler import LineProfiler
from nanowatch.output.formatter import print_summary, save_to_file


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------

class TestTimer:
    def test_duration_is_positive(self):
        timer = Timer("test").start()
        time.sleep(0.001)
        record = timer.stop()
        assert record.duration_ns > 0

    def test_duration_units_are_consistent(self):
        timer = Timer("units").start()
        time.sleep(0.001)
        record = timer.stop()
        assert record.duration_us == pytest.approx(record.duration_ns / 1_000, rel=1e-6)
        assert record.duration_ms == pytest.approx(record.duration_ns / 1_000_000, rel=1e-6)
        assert record.duration_s == pytest.approx(record.duration_ns / 1_000_000_000, rel=1e-6)

    def test_context_manager_stops_automatically(self):
        with Timer("ctx") as timer:
            time.sleep(0.001)
        assert timer.record is not None
        assert timer.record.duration_ns > 0

    def test_best_human_duration_selects_ns_for_tiny(self):
        record = TimingRecord(name="x", start_ns=0, end_ns=500)
        value, unit = record.best_human_duration()
        assert unit == "ns"
        assert value == 500

    def test_best_human_duration_selects_ms_for_medium(self):
        record = TimingRecord(name="x", start_ns=0, end_ns=5_000_000)
        value, unit = record.best_human_duration()
        assert unit == "ms"


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class TestCollector:
    def setup_method(self):
        self.col = Collector()

    def _make_record(self, name, ns):
        return TimingRecord(name=name, start_ns=0, end_ns=ns)

    def test_add_and_all(self):
        self.col.add(self._make_record("a", 100))
        assert len(self.col.all()) == 1

    def test_by_name_filters_correctly(self):
        self.col.add(self._make_record("a", 100))
        self.col.add(self._make_record("b", 200))
        self.col.add(self._make_record("a", 300))
        assert len(self.col.by_name("a")) == 2

    def test_stats_computes_correctly(self):
        self.col.add(self._make_record("fn", 100))
        self.col.add(self._make_record("fn", 300))
        stats = self.col.stats("fn")
        assert stats["count"] == 2
        assert stats["min_ns"] == 100
        assert stats["max_ns"] == 300
        assert stats["avg_ns"] == 200
        assert stats["total_ns"] == 400

    def test_stats_returns_none_for_unknown_name(self):
        assert self.col.stats("unknown") is None

    def test_clear_empties_records(self):
        self.col.add(self._make_record("a", 100))
        self.col.clear()
        assert self.col.all() == []


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

class TestDecorators:
    def setup_method(self):
        self.col = Collector()

    def test_watch_decorator_records_call(self):
        @watch(collector=self.col)
        def add(a, b):
            return a + b

        result = add(1, 2)
        assert result == 3
        assert len(self.col.all()) == 1

    def test_watch_with_custom_name(self):
        @watch("my.add", collector=self.col)
        def add(a, b):
            return a + b

        add(1, 2)
        assert self.col.all()[0].name == "my.add"

    def test_watch_no_args_uses_qualname(self):
        @watch
        def standalone():
            pass

        assert callable(standalone)

    def test_watch_block_records_duration(self):
        with watch_block("block test", collector=self.col):
            time.sleep(0.001)

        assert len(self.col.all()) == 1
        assert self.col.all()[0].duration_ms > 0

    def test_watch_call_returns_result(self):
        def multiply(a, b):
            return a * b

        result = watch_call(multiply, 3, 4, collector=self.col)
        assert result == 12
        assert len(self.col.all()) == 1

    def test_async_watch_decorator(self):
        @watch(collector=self.col)
        async def async_fn():
            await asyncio.sleep(0.001)
            return 42

        result = asyncio.run(async_fn())
        assert result == 42
        assert len(self.col.all()) == 1


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class TestWatchedMixin:
    def test_public_methods_are_instrumented(self):
        col = Collector()

        class MyService(WatchedMixin):
            _watch_collector = col
            _watch_prefix = "MyService"

            def do_work(self):
                return "done"

            def _private(self):
                return "skip"

        svc = MyService()
        svc.do_work()
        svc._private()

        assert len(col.all()) == 1
        assert col.all()[0].name == "MyService.do_work"

    def test_private_methods_are_skipped(self):
        col = Collector()

        class Svc(WatchedMixin):
            _watch_collector = col

            def pub(self):
                pass

            def _priv(self):
                pass

        Svc().pub()
        Svc()._priv()
        assert all(not r.name.endswith("_priv") for r in col.all())


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class TestWsgiMiddleware:
    def test_times_wsgi_request(self):
        col = Collector()

        def inner_app(environ, start_response):
            start_response("200 OK", [])
            return [b"hello"]

        wrapped = WsgiMiddleware(inner_app, collector=col)
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": "/test"}
        results = wrapped(environ, lambda *a: None)
        assert results == [b"hello"]
        assert len(col.all()) == 1
        assert "GET" in col.all()[0].name


class TestAsgiMiddleware:
    def test_times_asgi_http_request(self):
        col = Collector()

        async def inner_app(scope, receive, send):
            pass

        wrapped = AsgiMiddleware(inner_app, collector=col)
        scope = {"type": "http", "method": "POST", "path": "/submit"}

        asyncio.run(wrapped(scope, None, None))
        assert len(col.all()) == 1
        assert "POST" in col.all()[0].name

    def test_skips_non_http_scope(self):
        col = Collector()

        async def inner_app(scope, receive, send):
            pass

        wrapped = AsgiMiddleware(inner_app, collector=col)
        scope = {"type": "websocket"}

        asyncio.run(wrapped(scope, None, None))
        assert len(col.all()) == 0


# ---------------------------------------------------------------------------
# LineProfiler
# ---------------------------------------------------------------------------

class TestLineProfiler:
    def test_mark_records_checkpoints(self):
        col = Collector()
        prof = LineProfiler("session", collector=col)
        time.sleep(0.001)
        prof.mark("step one")
        time.sleep(0.001)
        prof.mark("step two")
        prof.finish()

        assert len(col.all()) == 2
        assert "step one" in col.all()[0].name
        assert "step two" in col.all()[1].name


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

class TestFileOutput:
    def test_save_to_file_creates_valid_json(self, tmp_path):
        col = Collector()
        col.add(TimingRecord("op", start_ns=0, end_ns=1_000_000))

        output_file = str(tmp_path / "results.json")
        save_to_file(col, output_file)

        with open(output_file) as f:
            data = json.load(f)

        assert data["total_measurements"] == 1
        assert data["records"][0]["name"] == "op"
        assert data["records"][0]["duration_ms"] == pytest.approx(1.0, rel=1e-3)