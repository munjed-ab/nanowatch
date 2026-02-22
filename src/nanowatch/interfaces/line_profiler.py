"""
Checkpoint-based profiler for measuring time between named points.

Useful when you want to profile individual lines or logical steps
inside a function without wrapping each in its own block.

Usage:
    prof = LineProfiler("process order")
    prof.mark("validated input")
    do_validation()
    prof.mark("queried db")
    result = db.query(...)
    prof.mark("serialized response")
    data = serialize(result)
    prof.finish()
"""

import time
from typing import Optional

from ..core.collector import Collector, default_collector
from ..core.timer import TimingRecord
from ..output.formatter import print_record, _separator


class LineProfiler:
    """
    Records elapsed time between consecutive named checkpoints.

    Each call to mark() captures the duration since the previous mark
    (or since start) as an individual TimingRecord.
    """

    def __init__(self, session_name: str, collector: Optional[Collector] = None):
        """
        Initialize and immediately start the profiler.

        Args:
            session_name: Name used as a prefix for all checkpoint labels
            collector: Collector to store records; defaults to global
        """
        self._session = session_name
        self._collector = collector or default_collector
        self._last_ns: int = time.perf_counter_ns()
        self._marks: list[str] = []

    def mark(self, checkpoint_name: str) -> TimingRecord:
        """
        Record time elapsed since the last mark (or session start).

        Args:
            checkpoint_name: Descriptive label for this checkpoint

        Returns:
            The completed TimingRecord for this segment
        """
        now_ns = time.perf_counter_ns()
        label = f"{self._session} | {checkpoint_name}"
        record = TimingRecord(
            name=label,
            start_ns=self._last_ns,
            end_ns=now_ns,
            context={"session": self._session, "checkpoint": checkpoint_name},
        )
        self._last_ns = now_ns
        self._marks.append(checkpoint_name)
        self._collector.add(record)
        print_record(record)
        return record

    def finish(self) -> None:
        """
        Print a separator line to visually close the profiling session.

        Does not add a final measurement; call mark() before finish()
        if you need to capture the last segment.
        """
        print(f"  [nanowatch] session '{self._session}' complete "
              f"({len(self._marks)} checkpoints)")
        print(_separator("-"))