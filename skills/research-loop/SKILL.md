---
name: research-loop
description: Run the Recursive-style automated AI research loop — propose → implement → run → validate → record — on an optimization benchmark track (nanogpt speedrun, nanochat budget, or kernels). Use when asked to start, resume, or iterate the research loop, or to run autonomous optimization experiments against a benchmark. One invocation = one iteration; drive it with /loop (supervised) or a schedule (unattended).
---

# Research Loop — Recursive-cycle Orchestrator

One invocation of this skill executes **one full iteration** on one track. State lives on disk, never in conversation (per [deli-auto-research]: fresh session per iteration, zero interaction, log decisions instead of asking).

## Prerequisites (first run only)

1. Workdir initialized via the **benchmark-harness** skill (`setup_benchmarks.sh`), and `.research-loop/executor.sh` configured by the user for their compute backend (local CPU/GPU, GKE, Modal, SSH, ...). The executor is a user decision — if it's missing or unsuited to the track (e.g. the 8-GPU speedrun on a CPU-only executor), report that and stop; never pick a backend yourself.
2. A measured baseline in `baselines/<track>.json` — if missing, this iteration's job is to measure it (run the unmodified candidate, store the result via `score.py`), not to optimize.
3. `state/task_spec.md` with: track, target metric, stop conditions (iteration budget, metric target, spend cap).

## State files (extends deli-auto-research layout)

```
state/progress.json          {iteration, track, status, stale_count}
state/findings.jsonl         append-only: one line per iteration (schema below)
state/directions_tried.json  every direction ever attempted, with outcome
baselines/<track>.json       current best ACCEPTED result
candidates/<track>/          current best code (matches the baseline)
runs/<track>-<iter>.jsonl    raw multi-seed results per iteration
```

`findings.jsonl` line: `{"iter": N, "direction": "...", "hypothesis": "...", "result": {...}, "verdict": "ACCEPT|REJECT|FAILED", "reason": "...", "ts": "..."}`

## The iteration

### 1. Propose
Spawn the **idea-proposer** agent (Agent tool). It reads only `findings.jsonl` + `directions_tried.json` and returns 5 ranked directions. Pick the top one that is absent from `directions_tried.json`; append it there immediately (status `in_progress`) so a crashed iteration never retries silently.

### 2. Implement
Edit **only** `candidates/<track>/`. Keep the change minimal and single-hypothesis — one idea per iteration, or a REJECT teaches you nothing. Take a pre-edit snapshot: `git -C <workdir> diff` must later show the validator exactly what changed (init a throwaway git repo over candidates/ at setup if needed).

### 3. Run
Submit the track's payload through `.research-loop/executor.sh` (see benchmark-harness for the exact commands), ≥3 seeds (1 seed acceptable for the multi-GPU speedrun; note it in the finding). Poll minute-level for the first 3 minutes — kill and record `FAILED` on import errors/OOM rather than waiting out the timeout. Aggregate with `score.py`.

### 4. Validate
If `score.py` says `improved: true`, spawn the **experiment-validator** agent with: the candidate diff, `runs/<track>-<iter>.jsonl`, and `result.json`. It returns ACCEPT or REJECT with reasons. **Only ACCEPT promotes.** A REJECT for suspected reward hacking must be recorded verbatim in the finding.

### 5. Record
- ACCEPT → overwrite `baselines/<track>.json` with `result.json` fields; the candidate becomes the new best; commit the candidate snapshot.
- REJECT/FAILED/no-improvement → revert `candidates/<track>/` to the last accepted snapshot.
- Either way: append the finding, update `directions_tried.json` with the outcome, bump `progress.json` (`stale_count` +1 on no-ACCEPT, reset on ACCEPT).

## Loop mechanics

- **Supervised:** `/loop` re-invokes this skill; self-pace at one iteration per wakeup.
- **Unattended:** a scheduled agent runs `claude -p "/research-loop <workdir> <track>" --dangerously-skip-permissions` per iteration — fresh session each time; disk state is the only memory.
- **Stall rule (deli):** `stale_count >= 3` → the proposer must be told to switch category entirely (see its category list); `stale_count >= 6` → switch track or stop and report.
- **Stop when:** task_spec's iteration budget or metric target is hit, or the compute budget defined in task_spec is reached. Write a final summary to `state/summary.md`.

## Hard rules

- Never edit `benchmarks/`, `baselines/`, or `runs/` — the plugin hook blocks these; treat a block as "wrong approach", not an obstacle.
- Suspected harness bug? Log `level=decision` in the finding and continue on another direction — never "fix" the harness mid-loop.
- Zero interaction: no questions, no plan mode; decisions are logged, not asked.
