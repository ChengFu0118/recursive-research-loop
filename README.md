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

For local development, point the marketplace at your checkout instead:

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

Permissions can't ship inside a plugin. Add to your project or user `settings.json` in the workdir where experiments run:

```json
{
  "permissions": {
    "allow": [
      "Bash(modal run:*)",
      "Bash(modal deploy:*)",
      "Bash(python3 scripts/*:*)"
    ]
  }
}
```

## Design principles

- **Separate execution from evaluation** — the agent that writes candidate code never scores it.
- **State lives in the experiment workdir**, not this repo: `state/`, `findings.jsonl`, `directions_tried.json`, benchmark checkouts.
- **Fresh session per iteration** — never rely on conversation resume; inject curated state from disk.
- **Guard the harness** — scoring scripts and reference implementations are read-only to the work agent.
