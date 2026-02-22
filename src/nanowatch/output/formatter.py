"""
Minimalist output renderer for timing results.

Handles both console output and file persistence.
All formatting decisions are centralized here.
Color output uses ANSI codes via colorama for Windows compatibility.
Console width is detected dynamically from the terminal.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from ..core.collector import Collector
from ..core.timer import TimingRecord

try:
    import colorama
    colorama.init(autoreset=True)
    _COLOR_AVAILABLE = True
except ImportError:
    _COLOR_AVAILABLE = False


class _Color:
    """ANSI color constants. Empty strings when color is unavailable."""

    if _COLOR_AVAILABLE:
        RESET   = colorama.Style.RESET_ALL
        DIM     = colorama.Style.DIM
        BOLD    = colorama.Style.BRIGHT
        CYAN    = colorama.Fore.CYAN
        GREEN   = colorama.Fore.GREEN
        YELLOW  = colorama.Fore.YELLOW
        RED     = colorama.Fore.RED
        WHITE   = colorama.Fore.WHITE
        MAGENTA = colorama.Fore.MAGENTA
    else:
        RESET = DIM = BOLD = CYAN = GREEN = YELLOW = RED = WHITE = MAGENTA = ""


def _console_width() -> int:
    """Return current terminal width, with a sensible fallback."""
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def _separator(char: str = "-") -> str:
    """Return a separator line sized to the current terminal width."""
    return char * _console_width()


_THRESHOLD_FAST_NS   = 1_000_000        # under 1 ms   -> green
_THRESHOLD_MEDIUM_NS = 10_000_000       # under 10 ms  -> yellow
                                        # 10 ms and above -> red


def _color_for_duration(ns: int) -> str:
    """Return the appropriate color code based on how slow the measurement is."""
    if ns < _THRESHOLD_FAST_NS:
        return _Color.GREEN
    if ns < _THRESHOLD_MEDIUM_NS:
        return _Color.YELLOW
    return _Color.RED


def _format_duration(ns: int) -> str:
    """Return a human-readable string for a nanosecond duration."""
    if ns < 1_000:
        return f"{ns} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:.3f} us"
    if ns < 1_000_000_000:
        return f"{ns / 1_000_000:.3f} ms"
    return f"{ns / 1_000_000_000:.6f} s"


def _colored_duration(ns: int) -> str:
    """Return a color-coded human-readable duration string."""
    color = _color_for_duration(ns)
    return f"{color}{_format_duration(ns)}{_Color.RESET}"


def _format_record_line(record: TimingRecord) -> str:
    """Render a single record as a compact colored one-line string."""
    value, unit = record.best_human_duration()
    raw_duration = f"{value:>10} {unit}"
    colored_duration = f"{_color_for_duration(record.duration_ns)}{raw_duration}{_Color.RESET}"

    name_str = f"{_Color.CYAN}{record.name:<40}{_Color.RESET}"

    context_str = ""
    if record.context:
        parts = [f"{k}={v}" for k, v in record.context.items()]
        context_str = f"  {_Color.DIM}[{', '.join(parts)}]{_Color.RESET}"

    return f"  {name_str} {colored_duration}{context_str}"


def _format_stats_block(name: str, stats: dict) -> str:
    """Render aggregate stats for a group of same-named records."""
    avg_ns = stats["avg_ns"]
    lines = [
        f"  {_Color.CYAN}{_Color.BOLD}{name}{_Color.RESET}",
        f"    calls : {_Color.WHITE}{stats['count']}{_Color.RESET}",
        f"    min   : {_Color.GREEN}{_format_duration(stats['min_ns'])}{_Color.RESET}",
        f"    max   : {_color_for_duration(stats['max_ns'])}{_format_duration(stats['max_ns'])}{_Color.RESET}",
        f"    avg   : {_color_for_duration(avg_ns)}{_format_duration(avg_ns)}{_Color.RESET}",
        f"    total : {_Color.WHITE}{_format_duration(stats['total_ns'])}{_Color.RESET}",
    ]
    return "\n".join(lines)


def print_record(record: TimingRecord) -> None:
    """Print a single timing record to stdout immediately."""
    print(_format_record_line(record))


def print_summary(collector: Collector) -> None:
    """Print a full summary report to stdout from all collected records."""
    records = collector.all()
    thick = _separator("=")
    thin  = _separator("-")

    if not records:
        print(f"  {_Color.DIM}[nanowatch] No measurements recorded.{_Color.RESET}")
        return

    print(f"{_Color.MAGENTA}{thick}{_Color.RESET}")
    print(f"  {_Color.BOLD}{_Color.WHITE}nanowatch{_Color.RESET} | Performance Summary")
    print(f"  {_Color.DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{_Color.RESET}")
    print(f"{_Color.MAGENTA}{thick}{_Color.RESET}")

    grouped = collector.grouped()
    for name, group in grouped.items():
        if len(group) == 1:
            print(_format_record_line(group[0]))
        else:
            stats = collector.stats(name)
            print(_format_stats_block(name, stats))
        print(f"{_Color.DIM}{thin}{_Color.RESET}")

    total_ns = sum(r.duration_ns for r in records)
    print(f"  Total tracked time : {_colored_duration(total_ns)}")
    print(f"  Total measurements : {_Color.WHITE}{len(records)}{_Color.RESET}")
    print(f"{_Color.MAGENTA}{thick}{_Color.RESET}")


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

    print(f"  {_Color.GREEN}[nanowatch] Results saved -> {output_path.resolve()}{_Color.RESET}")