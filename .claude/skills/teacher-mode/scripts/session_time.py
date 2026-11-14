"""Measure how long WYD teacher-mode sessions lasted, from Claude Code transcripts.

Claude Code writes every session to ~/.claude/projects/<cwd-slug>/<session-id>.jsonl,
and every line carries an ISO "timestamp". This script reads those timestamps.

    python3 session_time.py            # the current (most recently written) session
    python3 session_time.py --all      # every WYD session, oldest first, plus totals

"Active" time sums only the gaps shorter than BREAK_MINUTES, so long pauses
(dinner, sleep, an open laptop) don't count as study time. It's an estimate:
a long stretch of coding without messaging Claude also counts as a break.
"""

from __future__ import annotations  # macOS system python3 may predate `X | None`

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
PROJECT_MARKER = "wyd-chat-app"
BREAK_MINUTES = 45
TIMESTAMP_RE = re.compile(r'"timestamp":"([^"]+)"')


def transcripts() -> list[Path]:
    files = [
        f
        for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and PROJECT_MARKER in d.name
        for f in d.glob("*.jsonl")
    ]
    return sorted(files, key=lambda f: f.stat().st_mtime)


def timestamps(path: Path) -> list[datetime]:
    text = path.read_text(errors="ignore")
    return sorted(
        datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone()
        for t in TIMESTAMP_RE.findall(text)
    )


def summarize(path: Path) -> dict | None:
    ts = timestamps(path)
    if len(ts) < 2:
        return None
    limit = timedelta(minutes=BREAK_MINUTES)
    gaps = list(zip(ts, ts[1:]))
    active = sum((b - a for a, b in gaps if b - a < limit), timedelta())
    breaks = [(a, b - a) for a, b in gaps if b - a >= limit]
    return {
        "file": path.name,
        "start": ts[0],
        "end": ts[-1],
        "wall": ts[-1] - ts[0],
        "active": active,
        "breaks": breaks,
    }


def fmt(td: timedelta) -> str:
    minutes = int(td.total_seconds() // 60)
    return f"{minutes // 60}h{minutes % 60:02d}m"


def line(s: dict) -> str:
    breaks = ", ".join(f"{a:%H:%M} +{fmt(d)}" for a, d in s["breaks"]) or "none"
    return (
        f"{s['start']:%Y-%m-%d %H:%M}–{s['end']:%H:%M}  "
        f"wall {fmt(s['wall'])}  active {fmt(s['active'])}  breaks: {breaks}  ({s['file'][:8]})"
    )


def main() -> None:
    files = transcripts()
    if not files:
        sys.exit(f"No transcripts found under {PROJECTS_DIR} for '{PROJECT_MARKER}'.")
    if "--all" in sys.argv:
        summaries = [s for f in files if (s := summarize(f))]
        summaries.sort(key=lambda s: s["start"])
        for s in summaries:
            print(line(s))
        total = sum((s["active"] for s in summaries), timedelta())
        print(f"\n{len(summaries)} sessions, total active {fmt(total)}")
    else:
        s = summarize(files[-1])
        print(line(s) if s else "Current session has too few messages to measure.")


if __name__ == "__main__":
    main()
