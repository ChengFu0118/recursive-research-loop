# recursive-research-loop

A Claude Code plugin for running a **Recursive-style automated AI research loop** — propose → implement → run → validate → learn — on optimization benchmarks, inspired by [First Steps Toward Automated AI Research](https://www.recursive.com/articles/first-steps-toward-automated-ai-research).

Target benchmark tracks:

| Track | Task | Metric |
|---|---|---|
| NanoGPT speedrun | Train to fixed 3.28 val loss as fast as possible | Wall-clock time |
| NanoChat autoresearch | Minimize val loss in a 5-minute GPU budget | Bits per byte (BPB) |
| GPU kernel optimization | Optimize kernels toward hardware limits (KernelBench-style) | Speed-of-Light ratio |

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
- `research-loop` — the Recursive-cycle orchestrator: one invocation = one propose → implement → run → validate → record iteration; drive with `/loop` (supervised) or a schedule (unattended)
- `benchmark-harness` — backend-agnostic eval environments and scoring for the three tracks. Payloads (correctness/timing/log-parsing) are backend-neutral Python; **where they run is a user-defined executor** (`.research-loop/executor.sh`): local CPU/GPU by default, with GKE and Modal templates in `scripts/executors/`. `score.py` enforces multi-seed + noise-threshold promotion rules
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

- **`protect_eval.py` (PreToolUse)** — blocks any Edit/Write to the evaluation harness: `benchmarks/**/eval/**`, `benchmarks/**/reference/**`, `benchmarks/**/score_*.py`, plus any regexes you list in `.research-loop/protected-paths.txt` in the workdir. This is the structural anti-reward-hacking guard; it is enforced even under `--dangerously-skip-permissions`.
- **`post_edit_check.py` (PostToolUse)** — instant `py_compile` syntax check on edited `.py` files under `candidates/`, `kernels/`, or `submissions/`, so broken code is caught in milliseconds instead of failing a benchmark run on remote compute.

Both hooks are scoped to loop-specific paths, so a user-scope install stays silent in unrelated projects. Escape hatch for harness development: `RESEARCH_LOOP_DISABLE_GUARDS=1`.

### Agents

- `experiment-validator` — independent auditor (read-only tools): verifies stats from raw runs, screens the candidate diff for reward-hacking patterns, demands a plausible mechanism; only its ACCEPT promotes a result to baseline
- `idea-proposer` — fresh-context hypothesis generator: 5 ranked directions per iteration, forced category spread, no mechanism-level repeats, builds on accepted wins

### MCP servers

- `context7` — live Triton / CUDA / PyTorch documentation lookup (the innovation surface of all three tracks moves faster than model training data)

### Getting started with a loop

```bash
mkdir ~/experiments/run1 && cd ~/experiments/run1
bash <plugin>/skills/benchmark-harness/scripts/setup_benchmarks.sh .

# YOU decide where experiments run. The default executor is local python3
# (CPU, or local GPU if torch sees one). To use other compute, replace it:
$EDITOR .research-loop/executor.sh   # templates: scripts/executors/{gke.sh.example,modal.py.example}

claude --dangerously-skip-permissions   # then: "run the research loop on the kernels track"
```

The executor is a one-file contract — `executor.sh <payload.py> [args...]`, run it where torch lives, stream stdout back — so any backend works: local machine, a GKE GPU node pool, Modal, SSH to a lab box. The agent never chooses or changes the backend; that's yours.

### Future work

- Verify payload entrypoints/log formats against current upstream repos (marked `# VERIFY:` inline)
- Full KernelBench problem-set import for the kernel track
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
      "Edit(benchmarks/**/eval/**)",
      "Edit(**/score_*.py)",
      "Write(benchmarks/**/eval/**)",
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
- **State lives in the experiment workdir**, not this repo: `state/`, `findings.jsonl`, `directions_tried.json`, benchmark checkouts.
- **Fresh session per iteration** — never rely on conversation resume; inject curated state from disk.
- **Guard the harness** — scoring scripts and reference implementations are read-only to the work agent.
