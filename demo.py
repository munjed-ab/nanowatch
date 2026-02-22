"""
nanowatch demo script.

Run this directly to see all interfaces in action:
    python demo.py
"""

import asyncio
import time

import nanowatch
from nanowatch import (
    watch,
    watch_block,
    watch_call,
    WatchedMixin,
    LineProfiler,
)


# --- 1. Function decorator ---------------------------------------------------

@watch
def fibonacci(n):
    """Compute nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci.__wrapped__(n - 1) + fibonacci.__wrapped__(n - 2)


@watch("sum of range")
def heavy_sum(limit):
    """Sum a large range."""
    return sum(range(limit))


# --- 2. Async decorator ------------------------------------------------------

@watch("async fetch simulation")
async def fake_fetch(url):
    """Simulate an async HTTP request."""
    await asyncio.sleep(0.005)
    return f"response from {url}"


# --- 3. Class mixin ----------------------------------------------------------

class DataPipeline(WatchedMixin):
    """Sample data pipeline with auto-timed methods."""

    _watch_prefix = "DataPipeline"

    def load(self, source):
        """Simulate data loading."""
        time.sleep(0.002)
        return [1, 2, 3]

    def transform(self, data):
        """Simulate a transformation step."""
        time.sleep(0.001)
        return [x * 2 for x in data]

    def save(self, data):
        """Simulate saving output."""
        time.sleep(0.001)


# --- 4. Line profiler --------------------------------------------------------

def process_order(order_id):
    """Simulate a multi-step order processing flow."""
    prof = LineProfiler(f"process_order({order_id})")

    time.sleep(0.003)
    prof.mark("validated input")

    time.sleep(0.005)
    prof.mark("queried inventory")

    time.sleep(0.002)
    prof.mark("wrote to db")

    time.sleep(0.001)
    prof.mark("sent notification")

    prof.finish()


# --- run everything ----------------------------------------------------------

def main():
    """Execute all demos and print a final summary."""
    print("\n--- decorator ---")
    print("\nheavy_sum")
    heavy_sum(1_000_000)
    heavy_sum(5_000_000)
    heavy_sum(10_000_000)
    print("\nfibonacci")
    fibonacci(20)
    fibonacci(25)

    print("\n--- async ---")
    asyncio.run(fake_fetch("https://api.example.com/data"))

    print("\n--- watch_block ---")
    with watch_block("json serialization simulation"):
        time.sleep(0.002)

    print("\n--- watch_call ---")
    watch_call(sorted, [3, 1, 4, 1, 5, 9], name="sort list")

    print("\n--- mixin ---")
    pipeline = DataPipeline()
    data = pipeline.load("source.csv")
    data = pipeline.transform(data)
    pipeline.save(data)

    print("\n--- line profiler ---")
    process_order(42)

    print("\n--- summary ---")
    nanowatch.summary()

    print("\n--- saving to file ---")
    nanowatch.save("perf_results.json")


if __name__ == "__main__":
    main()