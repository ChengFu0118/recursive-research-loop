#!/usr/bin/env python3
"""PreToolUse guard: block edits to the evaluation harness (anti-reward-hacking).

The work agent must optimize candidates only — scoring scripts, reference
implementations, and timing code are read-only to it. Runs even under
--dangerously-skip-permissions (PreToolUse hooks are not bypassed).

Blocked by default (relative to the session cwd):
  - benchmarks/**/eval/**        scoring + validation code
  - benchmarks/**/reference/**   reference implementations
  - benchmarks/**/score_*.py     scorers anywhere under benchmarks/
  - anything listed in .research-loop/protected-paths.txt (one regex per line)

Escape hatch for harness development: RESEARCH_LOOP_DISABLE_GUARDS=1
"""

import json
import os
import re
import sys

DEFAULT_PATTERNS = [
    r"(^|/)benchmarks/.*/eval(/|$)",
    r"(^|/)benchmarks/.*/reference(/|$)",
    r"(^|/)benchmarks/.*/score_[^/]*\.py$",
]


def main() -> None:
    if os.environ.get("RESEARCH_LOOP_DISABLE_GUARDS") == "1":
        return

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return

    cwd = data.get("cwd") or os.getcwd()
    rel = os.path.relpath(os.path.abspath(file_path), cwd)

    patterns = list(DEFAULT_PATTERNS)
    extra = os.path.join(cwd, ".research-loop", "protected-paths.txt")
    if os.path.isfile(extra):
        with open(extra) as f:
            patterns += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    for pat in patterns:
        if re.search(pat, rel) or re.search(pat, file_path):
            print(
                f"BLOCKED: '{rel}' is part of the evaluation harness (matched {pat!r}). "
                "Scoring scripts, reference implementations, and timing code are "
                "read-only to the work agent. Improve the candidate implementation "
                "instead. If you believe the harness itself is buggy, record a "
                "level=decision finding for human review — do not modify it.",
                file=sys.stderr,
            )
            sys.exit(2)


if __name__ == "__main__":
    main()
