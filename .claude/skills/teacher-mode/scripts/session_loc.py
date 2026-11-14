"""Count the lines of code written in WYD teacher-mode sessions, from git.

The session window (start–end) comes from the Claude Code transcript, via
session_time.py. Every commit inside that window is diffed and its changed lines
are classified as code, comment or blank.

    python3 session_loc.py           # current session: its commits + uncommitted work
    python3 session_loc.py --all     # one row per past session, plus totals

Rules (all approximate, it's a pace signal, not a scoreboard):
- Only source files count (CODE_GLOBS). .claude/, docs, lockfiles and config don't.
- "code" = added lines that aren't blank or comment-only (# or //). Docstrings
  count as code. Claude's TODO(test) blocks are comments, so they're excluded.
- Commits up to GRACE_MINUTES after the last message still count (people often
  commit and close the laptop without saying so).
- Only what reached the diff counts: code rewritten five times before committing
  shows up once. Churn inside a session is invisible.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_time import fmt, summarize, transcripts  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[4]
GRACE_MINUTES = 60
CODE_GLOBS = [
    f":(glob){project}/**/*.{ext}"
    for project in ("wyd-backend", "wyd-frontend")
    for ext in ("py", "sql", "ts", "tsx", "js", "jsx", "css")
]
COMMENT_PREFIXES = ("#", "//")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def empty() -> dict[str, int]:
    return {"code": 0, "comment": 0, "blank": 0, "deleted": 0}


def classify_diff(diff: str, counts: dict[str, int]) -> None:
    for raw in diff.splitlines():
        if raw.startswith(("+++", "---")):
            continue
        if raw.startswith("-"):
            if raw[1:].strip():
                counts["deleted"] += 1
        elif raw.startswith("+"):
            text = raw[1:].strip()
            if not text:
                counts["blank"] += 1
            elif text.startswith(COMMENT_PREFIXES):
                counts["comment"] += 1
            else:
                counts["code"] += 1


def commits_between(start: datetime, end: datetime) -> list[tuple[str, str]]:
    out = git(
        "log",
        "--no-merges",
        f"--since={start.isoformat()}",
        f"--until={end.isoformat()}",
        "--format=%h\t%s",
        "--",
        *CODE_GLOBS,
    )
    return [tuple(line.split("\t", 1)) for line in out.splitlines() if line]  # type: ignore[misc]


def commit_counts(sha: str) -> dict[str, int]:
    counts = empty()
    classify_diff(git("show", "--format=", "--unified=0", sha, "--", *CODE_GLOBS), counts)
    return counts


def uncommitted_counts() -> dict[str, int]:
    counts = empty()
    classify_diff(git("diff", "HEAD", "--unified=0", "--", *CODE_GLOBS), counts)
    untracked = git("ls-files", "--others", "--exclude-standard", "--", *CODE_GLOBS)
    for rel in untracked.splitlines():
        text = (REPO_ROOT / rel).read_text(errors="ignore")
        classify_diff("".join(f"+{line}\n" for line in text.splitlines()), counts)
    return counts


def add(total: dict[str, int], part: dict[str, int]) -> None:
    for key in total:
        total[key] += part[key]


def per_hour(code: int, active: timedelta) -> str:
    hours = active.total_seconds() / 3600
    return f"{code / hours:.0f}/h" if hours >= 0.25 else "n/a"


def describe(counts: dict[str, int]) -> str:
    return (
        f"+{counts['code']} code, +{counts['comment']} comment, "
        f"−{counts['deleted']} deleted"
    )


def current() -> None:
    files = transcripts()
    s = summarize(files[-1]) if files else None
    if not s:
        sys.exit("Current session has too few messages to measure.")
    total = empty()
    commits = commits_between(s["start"], datetime.now().astimezone())
    for sha, subject in commits:
        counts = commit_counts(sha)
        add(total, counts)
        print(f"  {sha} {subject}\n      {describe(counts)}")
    pending = uncommitted_counts()
    if any(pending.values()):
        print(f"  (uncommitted) {describe(pending)}")
        add(total, pending)
    print(
        f"\n{s['start']:%Y-%m-%d}  {len(commits)} commits  {describe(total)}  "
        f"active {fmt(s['active'])}  ≈ {per_hour(total['code'], s['active'])} code"
    )


def history() -> None:
    summaries = sorted(
        (s for f in transcripts() if (s := summarize(f))), key=lambda s: s["start"]
    )
    grand = empty()
    for i, s in enumerate(summaries):
        end = s["end"] + timedelta(minutes=GRACE_MINUTES)
        if i + 1 < len(summaries):
            end = min(end, summaries[i + 1]["start"])
        total = empty()
        commits = commits_between(s["start"], end)
        for sha, _ in commits:
            add(total, commit_counts(sha))
        add(grand, total)
        print(
            f"{s['start']:%Y-%m-%d %H:%M}  {len(commits):>2} commits  "
            f"{describe(total)}  active {fmt(s['active'])}  "
            f"≈ {per_hour(total['code'], s['active'])}"
        )
    print(f"\n{len(summaries)} sessions, total {describe(grand)}")


if __name__ == "__main__":
    history() if "--all" in sys.argv else current()
