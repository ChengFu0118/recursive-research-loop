---
name: experiment-harness
description: Run and score user-defined experiments for the research loop — any "optimize a metric" task (training runs, GPU kernels, data pipelines, ...). Backend-agnostic — experiments run through a user-defined executor (local CPU/GPU, GKE, Modal, SSH, ...). Invoke to set up a workdir, run a candidate, or aggregate multi-seed results. Infrastructure called by research-loop and research-loop-init.
user-invocable: false
---

# Experiment Harness

Runs and scores experiments. The experiment itself is the user's (defined in `experiment.yaml` by research-loop-init); this harness only guarantees that every run is measured identically. **All scoring goes through this harness — the loop never invents its own scoring.**

Two layers:

- **Payloads** (`scripts/payloads/`) — backend-neutral Python that executes one run and prints `RESULT_JSON:` lines. Owned by the harness.
- **Executor** (`.research-loop/executor.sh` in the workdir) — decides *where* a payload runs. **Owned by the user.** Never assume a backend; if the executor isn't configured for the compute the experiment needs, say so and stop — don't substitute your own choice.

## Executor contract

```
.research-loop/executor.sh <payload.py> [payload args...]
```

Requirements: run the payload in an environment with `python3` + the experiment's deps, stream its stdout back unmodified, exit with the payload's exit code. That's all — `exec python3 "$@"` (local), a `kubectl create job` wrapper (GKE), a Modal function, SSH — anything. Templates in `scripts/executors/`.

## Workdir layout (created by setup)

```
workdir/
├── experiment.yaml        # the experiment definition (written by research-loop-init)
├── reference/             # pristine checkout of the experiment — READ-ONLY (hook-enforced)
├── candidates/            # editable working copies — the ONLY place the work agent edits
├── baselines/             # <name>.json — current best accepted result
├── runs/                  # raw multi-seed RESULT_JSON lines per iteration
└── .research-loop/
    ├── executor.sh        # USER-DEFINED compute backend (default: local)
    └── protected-paths.txt
```

## Setup (once per workdir)

```bash
bash "$SKILL_DIR/scripts/setup_workdir.sh" <workdir> [<git-url> <name>]
```

Creates the skeleton, optionally clones the experiment's repo into `reference/<name>` and copies it to `candidates/<name>`, writes `protected-paths.txt` (protects `reference/`, `baselines/`, `runs/`), and installs the local executor as default. The user then reviews/replaces the executor.

## Payloads

**`run_and_parse.py`** — run any command under a wall-clock budget and extract the metric from its logs. Two modes:

```bash
# mode=best: metric is the best regex-matched value in the log
run_and_parse.py --workdir candidates/<name> --cmd "<run_cmd with {seed}>" \
  --budget-sec 600 --seed 0 --metric-regex "val_loss:([\d.]+)" --direction min --mode best

# mode=time-to-target: metric is wall-clock seconds until the value reaches --target
run_and_parse.py --workdir candidates/<name> --cmd "<run_cmd with {seed}>" \
  --budget-sec 3000 --seed 0 --metric-regex "val_loss:([\d.]+)" --direction min \
  --mode time-to-target --target 3.28
```

**`speedup_eval.py`** — for function-vs-reference experiments (kernels, transforms, any drop-in replacement): `reference/<problem>/reference.py` defines `get_inputs()` and `ref(*inputs)`; the candidate defines `run(*inputs)`. Correctness = `allclose`; metric = speedup vs reference.

Collect `RESULT_JSON:` lines from stdout into `runs/<name>-<iter>.jsonl` (strip the prefix). Poll early — most failures (import error, OOM, misconfigured executor) surface in the first minutes; kill and fix rather than waiting out a budget.

## Scoring contract

```bash
python3 "$SKILL_DIR/scripts/score.py" --runs runs/<name>-<iter>.jsonl \
  --baseline baselines/<name>.json --metric metric --direction <min|max>
```

Output `result.json`: `{metric, mean, std, n_seeds, all_correct, baseline_mean, delta, improved}`.
Rules enforced by the script — do not relax them:
- `n_seeds >= 3` or `improved` is always `false`
- any `correct: false` run → `improved: false`
- improvement must exceed `max(1%, 1 std)` of baseline — noise is not progress

Baselines and candidates are only comparable if measured through the **same executor on the same hardware** — changing the backend invalidates `baselines/`; re-measure.

## Hard rules

1. **Never edit anything under `reference/`** (or other protected paths) — the PreToolUse hook blocks it; a blocked edit means you were about to touch the harness, not that the hook is broken.
2. **A result is not real until `score.py` says `improved: true` AND the experiment-validator agent returns ACCEPT.**
3. The metric regex and run command come from `experiment.yaml`, verified during init's smoke test — don't improvise either mid-loop.
