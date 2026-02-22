"""
High-precision timer using perf_counter_ns for nanosecond accuracy.

Provides the lowest-level timing primitive used by all interfaces.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimingRecord:
    """
    Immutable record of a single timing measurement.

    Stores raw nanosecond values and computed human-readable duration.
    """

    name: str
    start_ns: int
    end_ns: int
    context: dict = field(default_factory=dict)

    @property
    def duration_ns(self) -> int:
        """Return raw nanosecond duration."""
        return self.end_ns - self.start_ns

    @property
    def duration_us(self) -> float:
        """Return duration in microseconds."""
        return self.duration_ns / 1_000

    @property
    def duration_ms(self) -> float:
        """Return duration in milliseconds."""
        return self.duration_ns / 1_000_000

    @property
    def duration_s(self) -> float:
        """Return duration in seconds."""
        return self.duration_ns / 1_000_000_000

    def best_human_duration(self) -> tuple[float, str]:
        """
        Return duration in the most readable unit.

        Selects the unit that keeps the value above 1.0 for readability.
        """
        if self.duration_ns < 1_000:
            return self.duration_ns, "ns"
        if self.duration_us < 1_000:
            return round(self.duration_us, 3), "us"
        if self.duration_ms < 1_000:
            return round(self.duration_ms, 3), "ms"
        return round(self.duration_s, 6), "s"


class Timer:
    """
    Context-manager and manual start/stop high-precision timer.

    Uses time.perf_counter_ns which is the most precise clock available
    for measuring elapsed time (not wall-clock time).
    """

    def __init__(self, name: str, context: Optional[dict] = None):
        """
        Initialize timer with a measurement name.

        Args:
            name: Label for this measurement
            context: Optional extra metadata attached to the record
        """
        self.name = name
        self.context = context or {}
        self._start_ns: Optional[int] = None
        self._record: Optional[TimingRecord] = None

    def start(self) -> "Timer":
        """Start the timer and return self for chaining."""
        self._start_ns = time.perf_counter_ns()
        return self

    def stop(self) -> TimingRecord:
        """Stop the timer and return the completed TimingRecord."""
        end_ns = time.perf_counter_ns()
        self._record = TimingRecord(
            name=self.name,
            start_ns=self._start_ns,
            end_ns=end_ns,
            context=self.context,
        )
        return self._record

    def __enter__(self) -> "Timer":
        """Start timing on context entry."""
        return self.start()

    def __exit__(self, *_) -> None:
        """Stop timing on context exit."""
        self.stop()

    @property
    def record(self) -> Optional[TimingRecord]:
        """Return the completed record, or None if not yet stopped."""
        return self._record