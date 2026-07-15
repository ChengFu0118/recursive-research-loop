---
name: benchmark-harness
description: Reproducible eval environments and scoring for the research-loop benchmark tracks — NanoGPT speedrun (wall-clock to fixed val loss), NanoChat 5-minute budget (BPB), and kernel optimization (speedup vs reference). Backend-agnostic — experiments run through a user-defined executor (local CPU/GPU, GKE, Modal, ...). Invoke to set up a workdir, run a candidate, or aggregate multi-seed results. Infrastructure called by the research-loop skill.
user-invocable: false
---

# Benchmark Harness

Sets up and scores the three benchmark tracks. **All scoring goes through this harness — the loop never invents its own scoring.**

The harness is split into two layers:

- **Payloads** (`scripts/payloads/`) — backend-neutral Python that does the actual eval (correctness, timing, log parsing) and prints `RESULT_JSON:` lines. Owned by the harness.
- **Executor** (`.research-loop/executor.sh` in the workdir) — decides *where* a payload runs. **Owned by the user.** Never assume a backend; if the executor isn't configured for the compute the task needs, say so and stop — don't substitute your own choice.

## Executor contract

```
.research-loop/executor.sh <payload.py> [payload args...]
```

Requirements: run the payload in an environment with `python3` + `torch` (+ track deps), stream its stdout back unmodified, exit with the payload's exit code. That's all — so it can be `exec python3 "$@"` (local), a `kubectl create job` wrapper (GKE), a Modal function, SSH to a box, anything.

Templates in `scripts/executors/`: `local.sh` (default, CPU or local GPU), `gke.sh.example` (Kubernetes Job on GKE), `modal.py.example`.

## Workdir layout (created by setup)

```
workdir/
├── benchmarks/            # pristine references + eval code — READ-ONLY (hook-enforced)
├── candidates/            # the ONLY place the work agent edits
├── baselines/             # <track>.json — current best accepted result
├── runs/                  # raw multi-seed results per iteration
└── .research-loop/
    ├── executor.sh        # USER-DEFINED compute backend (default: local)
    └── protected-paths.txt
```

## Setup (once per workdir)

```bash
bash "$SKILL_DIR/scripts/setup_benchmarks.sh" <workdir>
# then the user reviews/replaces <workdir>/.research-loop/executor.sh for their compute
```

## Running a candidate

```bash
X=.research-loop/executor.sh
P="$SKILL_DIR/scripts/payloads"

# Kernel track
"$X" "$P/kernel_eval.py" --reference benchmarks/kernels/<id>/reference.py \
     --candidate candidates/kernels/<id>.py --seeds 3

# NanoGPT speedrun
"$X" "$P/train_and_parse.py" --workdir candidates/nanogpt --parse nanogpt \
     --target-loss 3.28 --budget-sec 3000 --seed 0 \
     --cmd "torchrun --nproc_per_node=8 train_gpt.py --seed={seed}"

# NanoChat budget
"$X" "$P/train_and_parse.py" --workdir candidates/nanochat --parse nanochat \
     --budget-sec 300 --seed 0 --cmd "python train.py --seed={seed}"
```

Collect `RESULT_JSON:` lines from stdout into `runs/<track>-<iter>.jsonl` (strip the prefix). Poll early — most failures (import error, OOM, misconfigured executor) surface in the first minutes; kill and fix rather than waiting out a budget.

## Scoring contract

`scripts/score.py` aggregates multi-seed runs against the baseline:

```bash
python3 "$SKILL_DIR/scripts/score.py" --runs runs/kernels-17.jsonl \
  --baseline baselines/kernels.json --metric speedup --direction max
```

Output `result.json`: `{metric, mean, std, n_seeds, all_correct, baseline_mean, delta, improved}`.
Rules enforced by the script — do not relax them:
- `n_seeds >= 3` or `improved` is always `false`
- any `correct: false` run → `improved: false`
- improvement must exceed `max(1%, 1 std)` of baseline — noise is not progress

Baselines and candidates are only comparable if measured through the **same executor on the same hardware** — changing the backend invalidates `baselines/`; re-measure.

## Hard rules

1. **Never edit anything under `benchmarks/`** — the PreToolUse hook blocks it; a blocked edit means you were about to touch the harness, not that the hook is broken.
2. **A result is not real until `score.py` says `improved: true` AND the experiment-validator agent returns ACCEPT.**
3. Upstream repos move fast: verify entrypoints and log formats marked `# VERIFY:` in the payloads before the first run.
