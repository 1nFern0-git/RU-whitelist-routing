#!/usr/bin/env python3
"""
overlay_common.py - Shared helpers for applying custom include/exclude overlays.

Overlays live under custom/{geoip,geosite}/{include,exclude}/<category>.txt.
Filename (lowercase) == category name. Blank lines and '#' comments are ignored.
A missing overlay file is treated the same as an empty one.
"""
import os
import sys
from pathlib import Path


def warn(msg):
    """Print a non-fatal warning to stderr."""
    print(f"WARNING: {msg}", file=sys.stderr)


def fail(msg):
    """Print a fatal error and exit(1). Used for problems in our own overlays."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def append_step_summary(lines):
    """
    Append lines to the GitHub Actions step summary if running in CI.

    Args:
        lines: Iterable of strings (Markdown). No-op when not in Actions.
    """
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return
    try:
        with open(path, 'a', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
    except OSError as e:
        warn(f"could not write step summary: {e}")


def load_overlay_entries(overlay_dir, kind, category):
    """
    Load non-blank, non-comment entries for one overlay file.

    Args:
        overlay_dir: Path to custom/geoip or custom/geosite
        kind: 'include' or 'exclude'
        category: category name (lowercase, == filename stem)

    Returns:
        List of (lineno, text) tuples in file order. Empty if file is absent.
    """
    path = Path(overlay_dir) / kind / f"{category}.txt"
    if not path.exists():
        return []

    entries = []
    for lineno, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        text = raw.strip()
        if not text or text.startswith('#'):
            continue
        entries.append((lineno, text))
    return entries


class Counters:
    """Per-category tally of overlay actions, printed after each build."""

    def __init__(self):
        self.added = 0
        self.skipped_dup = 0
        self.removed = 0
        self.unmatched = 0

    def report_line(self, category):
        return (f"  {category:<24} "
                f"+{self.added} added, "
                f"{self.skipped_dup} dup-skipped, "
                f"-{self.removed} removed, "
                f"{self.unmatched} unmatched")

    def nonzero(self):
        return any((self.added, self.skipped_dup, self.removed, self.unmatched))
