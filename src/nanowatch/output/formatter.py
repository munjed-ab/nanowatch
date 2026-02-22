"""
Minimalist output renderer for timing results.

Handles both console output and file persistence.
All formatting decisions are centralized here.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.collector import Collector
from ..core.timer import TimingRecord

CONSOLE_WIDTH = 72
SEPARATOR = "-" * CONSOLE_WIDTH
THICK_SEPARATOR = "=" * CONSOLE_WIDTH


def _format_duration(ns: int) -> str:
    """Return a human-readable string for a nanosecond duration."""
    if ns < 1_000:
        return f"{ns} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:.3f} us"
    if ns < 1_000_000_000:
        return f"{ns / 1_000_000:.3f} ms"
    return f"{ns / 1_000_000_000:.6f} s"


def _format_record_line(record: TimingRecord) -> str:
    """Render a single record as a compact one-line string."""
    value, unit = record.best_human_duration()
    context_str = ""
    if record.context:
        parts = [f"{k}={v}" for k, v in record.context.items()]
        context_str = f"  [{', '.join(parts)}]"
    return f"  {record.name:<40} {value:>10} {unit}{context_str}"


def _format_stats_block(name: str, stats: dict) -> str:
    """Render aggregate stats for a group of same-named records."""
    lines = [
        f"  {name}",
        f"    calls : {stats['count']}",
        f"    min   : {_format_duration(stats['min_ns'])}",
        f"    max   : {_format_duration(stats['max_ns'])}",
        f"    avg   : {_format_duration(stats['avg_ns'])}",
        f"    total : {_format_duration(stats['total_ns'])}",
    ]
    return "\n".join(lines)


def print_record(record: TimingRecord) -> None:
    """Print a single timing record to stdout immediately."""
    print(_format_record_line(record))


def print_summary(collector: Collector) -> None:
    """Print a full summary report to stdout from all collected records."""
    records = collector.all()
    if not records:
        print("  [nanowatch] No measurements recorded.")
        return

    print(THICK_SEPARATOR)
    print("  nanowatch | Performance Summary")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(THICK_SEPARATOR)

    grouped = collector.grouped()
    for name, group in grouped.items():
        if len(group) == 1:
            print(_format_record_line(group[0]))
        else:
            stats = collector.stats(name)
            print(_format_stats_block(name, stats))
        print(SEPARATOR)

    total_ns = sum(r.duration_ns for r in records)
    print(f"  Total tracked time : {_format_duration(total_ns)}")
    print(f"  Total measurements : {len(records)}")
    print(THICK_SEPARATOR)


def save_to_file(collector: Collector, path: str) -> None:
    """
    Persist all records to a JSON file.

    Args:
        collector: The collector holding all records
        path: File path to write (will overwrite if exists)
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = collector.all()
    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_measurements": len(records),
        "records": [
            {
                "name": r.name,
                "duration_ns": r.duration_ns,
                "duration_us": round(r.duration_us, 3),
                "duration_ms": round(r.duration_ms, 3),
                "duration_s": round(r.duration_s, 9),
                "context": r.context,
            }
            for r in records
        ],
        "groups": {
            name: collector.stats(name)
            for name in collector.grouped()
        },
    }

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"  [nanowatch] Results saved -> {output_path.resolve()}")