---
name: deli-auto-research
description: Use for long-horizon autonomous research tasks that must run unattended across hours or days — research agents, multi-iteration exploration, automated paper drafting, or any pipeline that risks cognitive loops, stalling, or session-death from context compaction. Encodes the Deli AutoResearch protocol: zero-interaction execution, file-persisted state, heartbeat watchdog, and forced structural pivots when stuck. Source: https://victorchen96.github.io/auto_research/framework.html
---

# Deli AutoResearch — Long-Horizon Autonomous Protocol

A protocol framework for keeping an agent productive across multi-hour / multi-day runs without human babysitting. Targets three failure modes: **cognitive loops** (diminishing returns), **stalling** (looks alive, isn't), and **runtime fragility** (compaction kills the loop).

The root cause is missing engineering scaffolding, not model capability. Apply the rules below as engineering discipline, not advice.

## 1. Behavioral constraints (hard rules)

1. **Zero interaction.** No Plan Mode. No questions. Never end a turn with a question. Log decisions as `level=decision` entries — don't ask for approval.
2. **Ready means execute.** Once preparation is done, run. No "should I submit?" gates after a plan is formed.
3. **Callback means report-alive.** Every callback (timer, watchdog, iteration) first updates its own `last_seen` timestamp, then checks the liveness of peers, then restarts any that have timed out.
4. **Persist state to files, not conversation.** Never rely on `--resume`. Start each iteration as a fresh session and inject curated state from disk.
5. **Guardian / worker separation.** Patrol/watchdog agents may only (a) liveness-check, (b) restart, (c) nudge. They may never read or modify the worker's data files.

## 2. Architecture

```
orchestrator (every ~2h)
    ├── reads state/
    ├── detects stall → injects fresh direction
    └── spawns work agent (Task A/B/C) in a fresh session

heartbeat watchdog (durable cron, hourly)
    └── checks last_seen of every loop, restarts timeouts, nudges stalls

resident shell guard (L0, no session)
    └── if heartbeat itself stale > 2h → spawn emergency patrol
```

Three core decisions baked in:
- Separate **execution** from **evaluation** (different agents).
- Prefer **fresh session over resume** every iteration.
- Enforce **direction diversity** — record what's been tried, forbid repetition.

## 3. State file layout

Every autonomous task gets its own directory with this layout:

```
{task}/state/
├── task_spec.md           # goal / milestones / success criteria
├── progress.json          # {iteration, total_findings, status, stale_count}
├── findings.jsonl         # append-only findings
├── directions_tried.json  # tried directions (forbid repetition)
└── iteration_log.jsonl    # per-iteration summary

{task}/logs/
├── work.jsonl             # work agent (decisions tagged level=decision)
├── orchestrator.jsonl
└── heartbeat.jsonl
```

Log line format (one JSON per line):
```json
{"ts":"2026-06-29T17:00:00Z","source":"work","level":"decision","event":"pivot","detail":"..."}
```

`level` is one of: `info | warn | error | decision`.

## 4. Usage pattern

1. **Initialize.** Create the task directory; write `state/task_spec.md` (goal, milestones, success criteria) and an initial `progress.json` (`{iteration:0, total_findings:0, status:"new", stale_count:0}`).
2. **Orchestrator loop (~2h cadence).**
   - Read `progress.json`.
   - If `stale_count >= 3`, generate a fresh direction that differs from every entry in `directions_tried.json`.
   - Launch a work agent via the Agent tool with an explicit goal + completion criteria.
   - Write results back to state. **Zero interaction.**
3. **Heartbeat watchdog (durable cron, hourly).**
   - Write own timestamp to `heartbeat.jsonl`.
   - For each loop: compare `last_seen` against `interval × 3` — restart if exceeded.
   - Nudge any work session that has been silent > 2h.

## 5. Stall detection and forced pivots

| Mechanism          | Rule                                                                            |
| ------------------ | ------------------------------------------------------------------------------- |
| Stall detection    | iteration with 0 new findings or a metric drop → `stale_count += 1`             |
| Forced pivot       | `stale_count >= 2` → change structural constraint; `>= 4` → flag for human      |
| Direction diversity| new direction must differ from every entry in `directions_tried.json`           |
| Round cap          | single work session capped at **15 rounds or 30 minutes**, whichever comes first |

**Key heuristic: "Pivot structure, not tactics."** At repeated stalls, change the frame or the environment — not strategy parameters. Tweaking hyperparameters when the framing is wrong wastes runs.

## 6. Heartbeat watchdog (three layers)

| Layer | Form                       | Depends on        | Role                                                                  |
| ----- | -------------------------- | ----------------- | --------------------------------------------------------------------- |
| L0    | resident shell guard       | no session        | heartbeat stale > 2h → spawn emergency patrol via headless agent      |
| L1    | durable cron, hourly       | a living session  | check `last_seen`, restart timed-out loops, nudge stalls              |
| L2    | business loop              | own session       | each callback first updates its own `last_seen`                       |

**Stall rule:** no progress update > 2h **and** last output is a question → nudge subagent. Three consecutive nudges without progress → declare structurally stuck; stop nudging and reopen with a new direction. The 2h threshold is deliberately shorter than the 4h stuck-task threshold so nudges happen before declaring failure.

## 7. Subagent scheduling patterns

| Pattern | Use case               | Key idea                                                                                  |
| ------- | ---------------------- | ----------------------------------------------------------------------------------------- |
| A       | Goal-driven research   | inject tried directions; require verifiable findings; append to `findings.jsonl`          |
| B       | Parallel exploration   | fire multiple agents in one message (investigation, refutation, cross-domain analogy)     |
| C       | Long compute jobs      | minute-level polling immediately after submit; auto-diagnose, fix, resubmit               |
| D       | Verification           | post-iteration QA; an independent subagent audits the evidence chain                      |

Every subagent prompt **must** include: background, the verifiable deliverable, working directory, file/line caps, completion criteria.

## 8. Engineering constraints (six rules)

1. ≤ **5 large files per iteration**; no single file > **300 lines**.
2. State is **injected via files**, never carried in conversation history.
3. Validation (test / compile / check) runs **between** iterations, not just at the end.
4. Citation-like content is verified **every 20 entries** — never batched at the end.
5. With multiple candidate directions, **prefer diversity over deeper digging**.
6. Unresolvable external-dependency failures **escalate**: full report + notify owner + poll for reply. Never abandon silently.

## 9. Honest limits (be honest about these)

- Self-ratings are in-framework multi-persona simulated review — longitudinally comparable only, not an external quality claim.
- Longest continuous validated run: 72h, with 6 directional human inputs and zero operational intervention.
- Fabricated citations/data originate from the LLM; this framework makes external checking mechanical but does not eliminate the error source.
- Separation of duties relies on protocol constraints, not model self-discipline — enforce in code where possible.

## When to invoke

Trigger this skill the moment a task implies any of:
- "run unattended for hours/overnight"
- "keep iterating until X"
- "autonomous research agent"
- "multi-round paper drafting / experimentation pipeline"
- existing agent has stalled, looped, or died on compaction

For short bounded tasks (< 1 hour, one or two iterations), the overhead isn't worth it — use a normal Agent call instead.
