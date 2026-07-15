---
name: call-api
description: Use to drive many parallel Claude API calls for the paper pipeline — multi-model peer review (3–5 reviewer personas × N rounds) and horizon-scaling / multi-model experiments (hundreds–thousands of calls). The batched-inference engine behind peer-review-simulation and experiment-design. Invoke when a step needs to fan out real model calls, compare models, or collect graded rubric scores. Wraps the Anthropic Python SDK (credentials already in the env) with concurrency, retries, and JSONL logging.
---

# Call API (Skill #2)

The batched-inference workhorse for the paper pipeline. Two jobs:

1. **Multi-model peer review** — run 3–5 reviewer personas, optionally on different models, across N rounds; collect per-criterion scores.
2. **Horizon-scaling experiments** — fan out hundreds–thousands of calls across models × conditions × tasks × trials, then aggregate.

- **IN:** a prompt spec (system + user templates) + a job matrix (models × conditions × trials)
- **OUT:** append-only `results.jsonl` (one row per call) + a summary aggregation

## Credentials

The script uses the zero-arg `anthropic.Anthropic()` client, which resolves credentials from standard SDK env vars (`ANTHROPIC_API_KEY`, or `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`, or an `ant auth login` profile).

**Important:** Claude Code's own `/login` credentials are *not* automatically exported to Bash subprocesses. Before running the helper, make the credentials available to the shell — e.g. `export ANTHROPIC_API_KEY=…`, or `set -a; eval "$(ant auth print-credentials --env)"; set +a` if the `ant` CLI is set up. If auth isn't resolvable, the script doesn't crash — it records `"ok": false` with the auth error on each row, so you can fix creds and re-run with `--resume`. **Never** hardcode a key or prompt the user for one interactively; ask them to export it (`! export …`) instead.

Setup once: `python3 -m venv venv && ./venv/bin/pip install anthropic`, then run the helper with `./venv/bin/python` (system Python is PEP-668 externally-managed).

## Models (use exact IDs)

| Role | Model ID | Notes |
| ---- | -------- | ----- |
| Default / strongest | `claude-opus-4-8` | Reviewer R2/R4, hardest experiment conditions |
| Balanced, high-volume | `claude-sonnet-5` | Bulk experiment trials |
| Cheap / fast | `claude-haiku-4-5` | Simple classification, warm-up |

**Reviewer-model diversity is a hard rule** (peer-review anti-inflation): at least one persona must run on a *different* model than the others. Mixing `claude-opus-4-8` + `claude-sonnet-5` across personas satisfies it.

## Tooling

A helper script wraps the SDK with concurrency, retries, and JSONL logging:

```bash
# Multi-model peer review: personas × rounds against a draft
python3 .claude/skills/call-api/call_api.py review \
  --draft research/main.tex --rounds 5 --out research/state/review.jsonl

# Horizon-scaling experiment: a job matrix from a JSON spec
python3 .claude/skills/call-api/call_api.py experiment \
  --spec research/bench/spec.json --out research/bench/results.jsonl --concurrency 8
```

Key behaviors baked into the script:
- `anthropic.Anthropic()` zero-arg client (reads env creds).
- **Adaptive thinking** (`thinking={"type":"adaptive"}`) + `output_config={"effort":"high"}` for review/judgement calls.
- SDK auto-retries 429/5xx (`max_retries`); the script adds a bounded thread pool for concurrency.
- **Append-only JSONL** — every call writes one line immediately, so a crash mid-run loses nothing (mirrors `deli-auto-research` state discipline).
- `--resume` skips job keys already present in the output file.

## Peer-review workflow

1. Load the draft (or a section) as shared context — cache it (same prefix across all persona calls).
2. For each persona (R1 Experimentalist … R5 Newcomer), send its rubric as the system prompt; require a JSON verdict via `output_config.format` (score per criterion + overall).
3. Enforce anti-inflation in aggregation, not in the prompt: first-round cap 7.0, max +1.5/round, ≥1 unresolved weakness, ≥1 persona on a different model.
4. Median the persona overalls → round score. Emit the routed weakness list for `peer-review-simulation`.

## Experiment workflow (Path A — API study)

1. Define the matrix in `spec.json`: `models[]`, `conditions[]`, `tasks[]`, `trials`.
2. The script expands the cross-product (e.g. 5 models × 3 conditions × 20 tasks × 3 trials = 900 calls) and runs them through the pool.
3. Each row logs: job key, model, condition, task id, trial, response text, `usage`, latency.
4. Aggregate to `results.json` (mean ± std per cell) for `experiment-design` → hand figures to `academic-figures-and-tables`.

**Pre-register** the hypothesis and the statistical test before running (no HARKing) — that's `experiment-design`'s gate; this skill only executes the matrix.

## Cost & safety

- Estimate before large runs: `count_tokens` × per-model rate × call count. Report the estimate; for > ~1000 calls, surface it before launching.
- Keep `--concurrency` modest (8–16) to respect rate limits; the SDK backs off on 429 automatically.

## When to invoke

- `peer-review-simulation` needs real multi-persona / multi-model scores.
- `experiment-design` Path A needs the API job matrix executed.
- Any "run this prompt across N models/conditions and collect results" task.

For a single one-off model call, just call the SDK inline — this skill is for **fan-out**.
