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
- `deli-auto-research` — long-horizon autonomous protocol: file-persisted state, heartbeat watchdog, stall detection, forced pivots
- `experiment-design` — pre-registered hypothesis → execute → iterate → report loop
- `call-api` — parallel Claude API fan-out with concurrency, retries, JSONL logging
- `skill-router` — dispatches prose sub-tasks to the right skill
- `search-agent` — arXiv/DBLP/OpenReview reference retrieval and verification
- `static-file-service` — serve results dashboards and build artifacts locally

**Paper pipeline** (companion skills for writing up results)
- `scientific-paper-writing` — top-level orchestrator
- `literature-survey`, `paper-structure-and-logic`, `academic-figures-and-tables`, `peer-review-simulation`

### Planned (see roadmap)

- `research-loop` skill — the Recursive-cycle orchestrator (propose/implement/run/validate/record)
- `benchmark-harness` skill — Modal-based reproducible eval environments for the three tracks
- `experiment-validator` agent — independent reward-hacking and correctness auditor (read-only tools)
- `idea-proposer` agent — diversity-enforced hypothesis generation
- Eval-protection hook — PreToolUse block on edits to scoring/reference files

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

**Isolation is your real safety boundary.** Skip-permissions removes all confirmation, so run the loop in a disposable environment: a container/VM, or at minimum a dedicated workdir + throwaway git clone, with a Modal token scoped to a sandbox workspace and a spend limit set in the Modal dashboard.

## Design principles

- **Separate execution from evaluation** — the agent that writes candidate code never scores it.
- **State lives in the experiment workdir**, not this repo: `state/`, `findings.jsonl`, `directions_tried.json`, benchmark checkouts.
- **Fresh session per iteration** — never rely on conversation resume; inject curated state from disk.
- **Guard the harness** — scoring scripts and reference implementations are read-only to the work agent.
