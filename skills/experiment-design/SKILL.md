---
name: experiment-design
description: Use when adding original experiments to a paper — pre-registered hypothesis, multi-model API study, or GPU RL run. Four-stage loop — Design → Execute → Iterate → Report — producing results.json + experiment_summary.md (data only; figures/tables belong to a separate sub-skill). Adds +1.0–1.5 to reviewer score. Sub-skill of scientific-paper-writing.
---

# Experiment Design (Sub-skill 3)

A 4-stage loop: **Design (hypothesis) → Execute (API/GPU) → Iterate (adjust) → Report (structured JSON)**.

- **IN:** a conjecture or identified gap from the structure sub-skill
- **OUT:** `results.json` + `experiment_summary.md`

This sub-skill explicitly **does not** produce LaTeX tables or figures — that's `academic-figures-and-tables`.

## Stage 1 — Design (the most important stage)

Before any compute spends, the design doc must answer: **"which paper claim does this experiment support?"** If no claim, no experiment.

Spec the following before running:
- Hypothesis (falsifiable).
- Independent variables, dependent variables, control variables.
- Expected results (rough prediction).
- Statistical plan (test, α, sample size) **decided before running** — no HARKing.

**Design principles:** falsifiable, minimal first (smallest experiment that could refute), pre-registered, has a control condition.

## Stage 2 — Execute

| Path | Scale              | Use case                              |
| ---- | ------------------ | ------------------------------------- |
| A    | API — hours        | Multi-model comparison, prompt ablation |
| B    | GPU/RL — days      | Agent training, reward shaping        |

- **API recipe:** 3–5 frontier models × 2–3 conditions × 15–25 tasks × 3 trials.
- **GPU recipe:** cluster job submission with auto-monitoring loop; minute-level polling right after submit to catch failures fast.

## Stage 3 — Iterate

| Observation         | Action                                        |
| ------------------- | --------------------------------------------- |
| Ceiling effect      | Increase difficulty                           |
| Floor effect        | Decrease difficulty **or** check for bugs     |
| Not significant     | More trials **or** revise hypothesis          |
| Surprise finding    | Design follow-up                              |

**Cap at 5 iterations**, then accept the best result. Past 5, diminishing returns + risk of HARKing.

## Stage 4 — Report (data only)

`results.json` schema: `config + results + statistics + findings`.

`experiment_summary.md`: purpose, results, limitations. Explicitly note negative findings and ceiling/floor effects.

## Gate 2 — pre-integration checks

- Pre-registered, clear hypothesis
- Statistical test reported (p-value or CI)
- ≥ 3 trials with std
- No ceiling/floor effect
- Links to a specific paper claim
- (Bonus) surprise finding documented

## When to invoke

- Adding an original experiment to a paper that has only synthesis so far.
- Reviewer flagged: "no experiments", "experiment not rigorous", "missing baselines", "missing ablation".
- Validating a Conjecture introduced in `paper-structure-and-logic`.
