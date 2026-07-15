---
name: research-loop-init
description: Onboard an experiment for the research loop — interview the user to produce experiment.yaml, smoke-test their executor end-to-end (local, GCE, k8s/helm, Modal, ...), measure the baseline, and optionally create the unattended schedule. Resumable — re-invoking jumps to the first incomplete phase. Use before the first loop run, when the loop's readiness gate reports not-ready, or to change cadence / tear down the schedule.
---

# Research Loop Init — Interactive Onboarding

Everything that must happen **before** the loop can run unattended. This is the ONE phase of the system where asking the user questions is correct and expected — all debugging happens here, with a human, so it never has to happen at 3am in iteration 12.

**Never run this unattended.** In a headless/scheduled session, stop and report instead.

## Phase detection (always start here)

```bash
python3 "$PLUGIN_ROOT/skills/research-loop/scripts/readiness.py" status <workdir>
```

Jump to the first incomplete phase (`phase_needed`): `interview` → A, `trial` → B, `baseline` → C. If already `ready`, go to D (schedule design / re-design / teardown — ask which).

## Phase A — Interview → `experiment.yaml`

If the workdir doesn't exist yet, run the benchmark-harness `setup_benchmarks.sh` first (skip the clones for a custom experiment). Then capture the user's experiment as data:

```yaml
name: my-experiment
run_cmd: "python train.py --seed={seed}"   # anything: torchrun, helm install + kubectl logs, gcloud compute ssh ...
metric:
  name: val_loss
  regex: "val_loss:([\\d.]+)"              # group 1 = the value, matched against run logs
  direction: min                            # min | max; best match in the log wins
budget_sec: 600                             # hard wall-clock cap per run
seeds: 3                                    # promotion requires >=3 (score.py enforces)
editable: candidates/my-experiment/         # the ONLY paths the loop may modify
protected: []                               # extra regexes appended to .research-loop/protected-paths.txt
```

- The three built-in tracks are presets of this schema (nanogpt: `direction: min` on wall-clock with target loss; nanochat: `val bpb`; kernels: use the `kernel_eval.py` payload instead).
- Ask only what can't be inferred: look at the experiment's repo/scripts first, propose the yaml, let the user correct it.
- Append `protected` entries to `.research-loop/protected-paths.txt` (anti-reward-hack hook), and confirm the executor: `.research-loop/executor.sh` must run a payload where the experiment's deps live. GKE/Modal templates: benchmark-harness `scripts/executors/`.

## Phase B — Smoke test (unblock everything, once)

Run **one seed** end-to-end through the executor:

```bash
.research-loop/executor.sh "$PAYLOADS/train_and_parse.py" --workdir <editable-dir> \
  --cmd "<run_cmd>" --budget-sec <budget> --seed 0 \
  --metric-regex "<regex>" --direction <min|max>
```

Iterate **with the user** until one valid `RESULT_JSON` line with `correct: true` comes back. Typical blockers, in the order they usually appear: executor auth (gcloud login, kubeconfig, modal token) → image/deps missing (torch, experiment requirements) → quota/GPU availability → wrong entrypoint → metric regex matches nothing (fix the regex against the real log, show the user). Time the run.

On success:
```bash
python3 .../readiness.py stamp <workdir> --trial-passed --iteration-sec <measured>
```

## Phase C — Baseline

Run the **unmodified** experiment with the full `seeds` count, collect `RESULT_JSON` lines into `runs/<name>-baseline.jsonl`, then store the baseline via `score.py` (no baseline file → the output IS the baseline; write its `{mean, std, n_seeds, metric}` to `baselines/<name>.json`). Stamp:

```bash
python3 .../readiness.py stamp <workdir> --baseline-measured
```

Write `state/task_spec.md` with the user: target metric, iteration budget, stop conditions, spend cap.

## Phase D — Schedule (optional; explicit user confirmation REQUIRED)

Creating standing jobs is a user decision. Present the design first:

- **Cadence** = measured iteration wall-clock × 1.5, rounded up to a sane interval (from `trial_report.json`'s `iteration_wallclock_sec`).
- Show: iterations/day, estimated compute per day, the readiness checklist, and the teardown command.
- Ask ONE question: **create the schedule / run supervised with `/loop` instead / stop here**. Only a clear "create" creates anything.

On yes, create two jobs (via the `schedule` skill / scheduled agents, or crontab as fallback):
1. **Worker** (every cadence): `cd <workdir> && claude -p "Use the research-loop skill to run exactly ONE iteration on '<name>' in this workdir. Zero interaction." --dangerously-skip-permissions`
2. **Heartbeat** (hourly, guardian role): reads `state/progress.json` ONLY — restarts a stalled worker, nudges on `stale_count`, and when `status == "done"` **tears down both jobs**. It never reads or edits experiment data; the worker never edits scheduler config.

Record both job IDs in `state/schedule.json` so teardown/re-design can find them.

## Re-entry map

| Situation | What happens on re-invoke |
|---|---|
| Config drift (yaml/executor changed) | readiness reports `trial` — redo B (+C if metric semantics changed) |
| Trial done, user deferred scheduling | jumps straight to D |
| Schedule exists | offer: change cadence / teardown / nothing |
| User says "tear it down" | delete jobs from `state/schedule.json`, set `status: stopped` |
