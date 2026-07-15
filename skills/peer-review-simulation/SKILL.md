---
name: peer-review-simulation
description: Use to score a paper draft and produce a routed weakness list that drives the next iteration. Multi-persona scoring (3–5 reviewer personas, independent, no anchoring), median final score, anti-inflation rules, weakness routing back to literature/structure/experiment/figures sub-skills. Sub-skill of scientific-paper-writing.
---

# Peer Review Simulation (Sub-skill 5)

Multi-persona scoring that drives the iteration loop by routing weaknesses back to sub-skills #1–4.

- **IN:** compiled PDF
- **OUT:** score + weakness list, routed to the responsible sub-skill

## Reviewer personas (use 3–5 per round)

| Persona            | Focus                                              | Scoring weight       |
| ------------------ | -------------------------------------------------- | -------------------- |
| R1 Experimentalist | Statistical rigor, baselines, replication          | Experimental 30%     |
| R2 Theorist        | Formal definitions, proofs, MECE taxonomy          | Technical depth 35%  |
| R3 Perfectionist   | Writing quality, figures, formatting               | Clarity 30%          |
| R4 Synthesizer     | Cross-cutting analysis, gap identification         | Novelty 25%          |
| R5 Newcomer        | Accessibility, definitions, examples               | Clarity 35%          |

## Scoring protocol

- **Each reviewer scores independently** — no anchoring, no shared context.
- **Final score = median across reviewers** (robust to one outlier).
- Score across all dimensions: Novelty, Comprehensiveness, Clarity, Technical Depth, Experimental Validation.
- **Calibration:** 6.0 = workshop, 7.0 = main conference, 8.0 = Strong Accept (top 20%), 9.0 = Oral.

## Anti-inflation rules

These exist to keep the score honest across rounds:
- **First-round score capped at 7.0.**
- **Max +1.5 per round** (no leap-frogging).
- At least **1 "unresolved" weakness must remain** at the end of every round.
- At least **1 reviewer per round must use a different LLM model** than the others (perspective diversity).

## Output format

- Overall score + per-dimension scores.
- **3–5 Strengths**, **3–5 Weaknesses** (prioritized Major / Minor).
- Concrete, **actionable** suggestions (not "improve clarity" — name the section).
- Recommendation: Accept / Weak Accept / Borderline / Reject.
- **Regression check** on previously fixed weaknesses (don't let them sneak back).

## Routing weaknesses → sub-skills

Use the orchestrator's routing table — every weakness must map to exactly one sub-skill:

| Weakness                       | Sub-skill                  |
| ------------------------------ | -------------------------- |
| Citation coverage / arXiv / recency | `literature-survey`    |
| Structure / depth / taxonomy / claims | `paper-structure-and-logic` |
| No experiments / not rigorous  | `experiment-design`        |
| Tables / visualizations / error bars | `academic-figures-and-tables` |

## When to invoke

- End of any iteration that produced a compileable PDF.
- After integrating a fix, to confirm regression hasn't crept in.
- Before declaring a phase done (each phase has a score gate: 6.0 / 7.0 / 8.0 / 8.5).
