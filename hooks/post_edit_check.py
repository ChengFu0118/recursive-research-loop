#!/usr/bin/env python3
"""PostToolUse check: fast syntax check on edited candidate code.

Catches Python syntax errors immediately after an edit to candidate/kernel
code, before a GPU run is submitted — a failed compile on Modal wastes minutes
and money; py_compile here costs milliseconds.

Only fires for .py files under candidate directories (candidates/, kernels/,
submissions/) so a user-scope install stays quiet in unrelated projects.

Escape hatch: RESEARCH_LOOP_DISABLE_GUARDS=1
"""

import json
import os
import py_compile
import re
import sys

CANDIDATE_DIRS = re.compile(r"(^|/)(candidates|kernels|submissions)(/|$)")


def main() -> None:
    if os.environ.get("RESEARCH_LOOP_DISABLE_GUARDS") == "1":
        return

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path.endswith(".py"):
        return

    cwd = data.get("cwd") or os.getcwd()
    rel = os.path.relpath(os.path.abspath(file_path), cwd)
    if not CANDIDATE_DIRS.search(rel):
        return
    if not os.path.isfile(file_path):
        return

    try:
        py_compile.compile(file_path, doraise=True)
    except py_compile.PyCompileError as exc:
        print(
            f"SYNTAX ERROR in {rel} — fix before submitting a GPU run:\n{exc.msg}",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
