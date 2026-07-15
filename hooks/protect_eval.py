#!/usr/bin/env python3
"""PreToolUse guard: block edits to the evaluation harness (anti-reward-hacking).

The work agent must optimize candidates only — the reference checkout, stored
baselines, raw run results, and scoring code are read-only to it. Runs even
under --dangerously-skip-permissions (PreToolUse hooks are not bypassed).

Only active inside a research-loop workdir (a cwd containing .research-loop/),
so a user-scope install stays silent in unrelated projects. Inside a workdir,
blocked by default (relative to the session cwd):
  - reference/**, baselines/**, runs/**
  - score_*.py anywhere
  - anything listed in .research-loop/protected-paths.txt (one regex per line)

Escape hatch for harness development: RESEARCH_LOOP_DISABLE_GUARDS=1
"""

import json
import os
import re
import sys

DEFAULT_PATTERNS = [
    r"(^|/)reference(/|$)",
    r"(^|/)baselines(/|$)",
    r"(^|/)runs(/|$)",
    r"(^|/)score_[^/]*\.py$",
]


def main() -> None:
    if os.environ.get("RESEARCH_LOOP_DISABLE_GUARDS") == "1":
        return

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    cwd = data.get("cwd") or os.getcwd()
    loop_dir = os.path.join(cwd, ".research-loop")
    if not os.path.isdir(loop_dir):
        return  # not a research-loop workdir — stay silent

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return

    rel = os.path.relpath(os.path.abspath(file_path), cwd)

    patterns = list(DEFAULT_PATTERNS)
    extra = os.path.join(loop_dir, "protected-paths.txt")
    if os.path.isfile(extra):
        with open(extra) as f:
            patterns += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    for pat in patterns:
        if re.search(pat, rel):
            print(
                f"BLOCKED: '{rel}' is part of the evaluation harness (matched {pat!r}). "
                "The reference checkout, baselines, runs, and scoring code are "
                "read-only to the work agent. Improve the candidate implementation "
                "instead. If you believe the harness itself is buggy, record a "
                "level=decision finding for human review — do not modify it.",
                file=sys.stderr,
            )
            sys.exit(2)


if __name__ == "__main__":
    main()
