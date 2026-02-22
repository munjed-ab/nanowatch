# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-02-22

### Added
- High-precision Python performance measurement toolkit.
- Nanosecond accuracy using `time.perf_counter_ns`.
- Multiple interfaces: `@watch` decorator, `watch_block` context manager, `watch_call`.
- `WatchedMixin` for automatic class method instrumentation.
- WSGI (middleware) and ASGI (middleware) support for web frameworks.
- `LineProfiler` for checkpoint-based profiling within functions.
- Console summary reporting and JSON file persistence.

### Changed
- Rebranded from "perfwatch" to "nanowatch" to avoid PyPI name collision.
