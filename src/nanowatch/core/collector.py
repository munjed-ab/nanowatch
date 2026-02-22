"""
Central collector for all timing records produced during a session.

Stores records in-memory and exposes query helpers.
Designed to be injected as a singleton or scoped instance.
"""

from collections import defaultdict
from typing import Optional
from .timer import TimingRecord


class Collector:
    """
    Thread-safe store for TimingRecord instances.

    Receives records from all interfaces (decorators, middleware, etc.)
    and provides aggregation utilities for reporting.
    """

    def __init__(self):
        """Initialize with an empty records list."""
        self._records: list[TimingRecord] = []

    def add(self, record: TimingRecord) -> None:
        """Append a completed TimingRecord to the collection."""
        self._records.append(record)

    def all(self) -> list[TimingRecord]:
        """Return all collected records in insertion order."""
        return list(self._records)

    def by_name(self, name: str) -> list[TimingRecord]:
        """Return all records matching the given name."""
        return [r for r in self._records if r.name == name]

    def grouped(self) -> dict[str, list[TimingRecord]]:
        """Return records grouped by name."""
        groups: dict[str, list[TimingRecord]] = defaultdict(list)
        for record in self._records:
            groups[record.name].append(record)
        return dict(groups)

    def stats(self, name: str) -> Optional[dict]:
        """
        Compute aggregate stats for all records with the given name.

        Returns:
            Dict with count, min, max, avg, total in nanoseconds,
            or None if no records found.
        """
        records = self.by_name(name)
        if not records:
            return None

        durations = [r.duration_ns for r in records]
        return {
            "count": len(durations),
            "min_ns": min(durations),
            "max_ns": max(durations),
            "avg_ns": sum(durations) // len(durations),
            "total_ns": sum(durations),
        }

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()


# Module-level default collector used by all convenience interfaces.
default_collector = Collector()
