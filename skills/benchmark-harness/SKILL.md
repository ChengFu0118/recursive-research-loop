---
name: benchmark-harness
description: Reproducible eval environments and scoring for the research-loop benchmark tracks — NanoGPT speedrun (wall-clock to fixed val loss), NanoChat 5-minute budget (BPB), and Triton kernel optimization (speedup vs reference). Invoke to set up benchmarks in a workdir, submit a candidate to Modal for scoring, or aggregate multi-seed results. Infrastructure called by the research-loop skill.
user-invocable: false
---

# Benchmark Harness

Sets up and scores the three benchmark tracks. Everything runs on Modal (macOS host, remote NVIDIA GPUs). **All scoring goes through this harness — the loop never invents its own scoring.**

## Workdir layout (created by setup)

```
workdir/
├── benchmarks/            # pristine reference checkouts + eval code — READ-ONLY (hook-enforced)
│   ├── modded-nanogpt/    # KellerJordan/modded-nanogpt
│   ├── nanochat/          # karpathy/nanochat
│   └── kernels/           # kernel problems: <id>/reference.py
├── candidates/            # the ONLY place the work agent edits
│   ├── nanogpt/           # working copy of the training script
│   ├── nanochat/
│   └── kernels/           # <id>.py candidate kernels
├── baselines/             # <track>.json — current best accepted result
└── .research-loop/
    └── protected-paths.txt
```

## Setup (once per workdir)

```bash
bash "$SKILL_DIR/scripts/setup_benchmarks.sh" <workdir>
modal token new   # if not already authenticated
```

The setup script clones the benchmark repos, copies editable baselines into `candidates/`, and writes `protected-paths.txt` extending the eval-protection hook to the whole `benchmarks/` tree.

## Running a candidate

All entrypoints are in `scripts/modal_runner.py`:

```bash
# Kernel track: correctness vs reference + timed speedup, one GPU
modal run scripts/modal_runner.py::kernel_eval \
  --problem-dir benchmarks/kernels/<id> --candidate candidates/kernels/<id>.py --seeds 3

# NanoGPT speedrun: 8xH100, wall-clock to target val loss
modal run scripts/modal_runner.py::nanogpt_speedrun \
  --candidate-dir candidates/nanogpt --target-loss 3.28

# NanoChat: fixed 5-minute budget, report BPB
modal run scripts/modal_runner.py::nanochat_budget \
  --candidate-dir candidates/nanochat --budget-sec 300
```

Each run appends one JSON line to `runs/<track>-<iteration>.jsonl`. Poll minute-level right after submission — most failures (OOM, import error, shape mismatch) happen in the first two minutes; kill and fix rather than waiting out a dead run.

## Scoring contract

`scripts/score.py` aggregates multi-seed runs and compares against the baseline:

```bash
python3 scripts/score.py --runs runs/kernels-17.jsonl \
  --baseline baselines/kernels.json --metric speedup --direction max
```

Output `result.json`: `{metric, mean, std, n_seeds, all_correct, baseline_mean, delta, improved}`.
Rules enforced by the script — do not relax them:
- `n_seeds >= 3` or `improved` is always `false`
- any `correct: false` run → `improved: false`
- improvement must exceed `max(1%, 1 std)` of baseline — noise is not progress

## Hard rules

1. **Never edit anything under `benchmarks/`** — the PreToolUse hook blocks it; a blocked edit means you were about to touch the harness, not that the hook is broken.
2. **A result is not real until `score.py` says `improved: true` AND the experiment-validator agent returns ACCEPT.**
3. Upstream repos move fast: at setup time, verify the training entrypoint names and log formats in the cloned repos and adjust the `# VERIFY:` lines in `modal_runner.py` before the first run.
