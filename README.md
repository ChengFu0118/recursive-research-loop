# recursive-research-loop

A Claude Code plugin for running a **Recursive-style automated AI research loop** — propose → implement → run → validate → learn — on **any user-defined experiment**: an "optimize a metric" task described in one yaml file. Training runs, GPU kernels, data pipelines, inference latency — if a command produces a number in its logs, the loop can iterate on it. Inspired by [First Steps Toward Automated AI Research](https://www.recursive.com/articles/first-steps-toward-automated-ai-research).

You bring: a repo/script to optimize, a metric (log regex + direction), and a compute backend (a one-file executor: local, GKE, Modal, SSH, ...). The loop brings: hypothesis generation, implementation, multi-seed scoring, independent validation, and anti-reward-hacking guardrails.

Benchmarking the plugin itself (standard public benchmark suites, leaderboards, loop-quality reports) lives in a separate repo: `benchmark-autoresearch`.

## Install

```bash
# In Claude Code:
/plugin marketplace add ChengFu0118/recursive-research-loop
/plugin install recursive-research-loop@recursive-research-loop
```

### From the terminal (local clone)

If you've cloned the repo and have Claude Code installed, install it without entering an interactive session:

```bash
git clone https://github.com/ChengFu0118/recursive-research-loop.git "$GIT_ROOT/recursive-research-loop"
claude plugin marketplace add "$GIT_ROOT/recursive-research-loop"
claude plugin install recursive-research-loop@recursive-research-loop
```

This installs at **user scope** (available in every project). Use `-s project` to scope it to the current project instead, and `claude plugin list` to confirm. Since the marketplace points at your local checkout, `git pull` + `claude plugin update recursive-research-loop` picks up new versions.

For iterating on the plugin itself, the same local-path marketplace works from inside a session:

```bash
/plugin marketplace add /path/to/recursive-research-loop
```

## What's included

### Skills

**Research loop core**
- `research-loop-init` — interactive onboarding, run once per experiment: interview → `experiment.yaml`, smoke-test the executor end-to-end (local/GCE/k8s/helm/Modal), measure the baseline, and optionally create the unattended schedule (worker cadence + heartbeat watchdog). Resumable; re-invoke to change cadence or tear down.
- `research-loop` — the Recursive-cycle orchestrator: one invocation = one propose → implement → run → validate → record iteration; drive with `/loop` (supervised) or the schedule (unattended). **Gated**: every invocation runs the readiness detector first — if init hasn't completed (or config drifted since the trial), an interactive session routes into `research-loop-init` automatically; an unattended session fails fast with reasons.
- `experiment-harness` — runs and scores the user's experiment. Payloads (run-under-budget + metric extraction, or function-vs-reference speedup) are backend-neutral Python; **where they run is a user-defined executor** (`.research-loop/executor.sh`): local CPU/GPU by default, with GKE and Modal templates in `scripts/executors/`. `score.py` enforces multi-seed + noise-threshold promotion rules
- `deli-auto-research` — long-horizon autonomous protocol: file-persisted state, heartbeat watchdog, stall detection, forced pivots
- `experiment-design` — pre-registered hypothesis → execute → iterate → report loop
- `call-api` — parallel Claude API fan-out with concurrency, retries, JSONL logging
- `skill-router` — dispatches prose sub-tasks to the right skill
- `search-agent` — arXiv/DBLP/OpenReview reference retrieval and verification
- `static-file-service` — serve results dashboards and build artifacts locally

**Paper pipeline** (companion skills for writing up results)
- `scientific-paper-writing` — top-level orchestrator
- `literature-survey`, `paper-structure-and-logic`, `academic-figures-and-tables`, `peer-review-simulation`

### Hooks (active on install)

- **`protect_eval.py` (PreToolUse)** — blocks any Edit/Write to protected paths. The real configuration is per-workdir: `setup_workdir.sh` writes `.research-loop/protected-paths.txt` protecting `reference/`, `baselines/`, and `runs/`, and init appends the experiment's own `protected:` entries. This is the structural anti-reward-hacking guard; it is enforced even under `--dangerously-skip-permissions`.
- **`post_edit_check.py` (PostToolUse)** — instant `py_compile` syntax check on edited `.py` files under `candidates/`, `kernels/`, or `submissions/`, so broken code is caught in milliseconds instead of failing an experiment run on remote compute.

Both hooks are scoped to loop-specific paths, so a user-scope install stays silent in unrelated projects. Escape hatch for harness development: `RESEARCH_LOOP_DISABLE_GUARDS=1`.

### Agents

- `experiment-validator` — independent auditor (read-only tools): verifies stats from raw runs, screens the candidate diff for reward-hacking patterns, demands a plausible mechanism; only its ACCEPT promotes a result to baseline
- `idea-proposer` — fresh-context hypothesis generator: 5 ranked directions per iteration, forced category spread, no mechanism-level repeats, builds on accepted wins

### MCP servers

- `context7` — live documentation lookup for fast-moving libraries (Triton, CUDA, PyTorch, ...) during the implementation phase

### Getting started with a loop

```bash
mkdir -p ~/experiments/run1
bash <plugin>/skills/experiment-harness/scripts/setup_workdir.sh ~/experiments/run1 <your-experiment-git-url> myexp
cd ~/experiments/run1

# YOU decide where experiments run. The default executor is local python3.
# To use other compute, replace it:
$EDITOR .research-loop/executor.sh   # templates: scripts/executors/{gke.sh.example,modal.py.example}

claude   # then: "use research-loop-init to onboard my experiment"
```

Init interviews you into an `experiment.yaml`, smoke-tests the executor until one valid result comes back, measures the baseline, and (only if you say yes) creates the unattended schedule. After that, one prompt runs an iteration — or the schedule runs them for you.

The executor is a one-file contract — `executor.sh <payload.py> [args...]`, run it where the experiment's deps live, stream stdout back — so any backend works: local machine, a GKE GPU node pool, Modal, SSH to a lab box. The agent never chooses or changes the backend; that's yours.

### Future work

- Sync the harness with the `benchmark-autoresearch` companion repo (single source of truth)
- Findings dashboard via `static-file-service`

## Recommended settings

This plugin assumes the loop runs unattended with:

```bash
claude --dangerously-skip-permissions
```

so no `allow` list is needed — nothing prompts. What still matters is what **cannot** be bypassed: `permissions.deny` rules and PreToolUse hooks are enforced even in skip-permissions mode, and they are the only brakes on an autonomous run. Add to `settings.json` in the experiment workdir:

```json
{
  "permissions": {
    "deny": [
      "Edit(reference/**)",
      "Write(reference/**)",
      "Edit(**/score_*.py)",
      "Read(.env*)",
      "Bash(git push:*)"
    ]
  }
}
```

- The `Edit`/`Write` denies keep the work agent from touching scoring scripts and reference implementations — the structural anti-reward-hacking guardrail (the planned PreToolUse hook adds a second, smarter layer).
- `Read(.env*)` keeps credentials out of the loop's context.
- `Bash(git push:*)` keeps an unattended agent from publishing; review and push results yourself.

**Isolation is your real safety boundary.** Skip-permissions removes all confirmation, so run the loop in a disposable environment: a container/VM, or at minimum a dedicated workdir + throwaway git clone. Scope the credentials your executor uses to a sandbox project/workspace (e.g. a dedicated GCP project or Modal workspace) and set spend limits on that backend.

## Design principles

- **Separate execution from evaluation** — the agent that writes candidate code never scores it.
- **State lives in the experiment workdir**, not this repo: `state/`, `findings.jsonl`, `directions_tried.json`, experiment checkouts.
- **Fresh session per iteration** — never rely on conversation resume; inject curated state from disk.
- **Guard the harness** — scoring scripts and reference implementations are read-only to the work agent.
