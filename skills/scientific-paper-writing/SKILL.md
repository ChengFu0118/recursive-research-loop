---
name: scientific-paper-writing
description: Use when asked to draft, revise, or orchestrate a full scientific paper or survey (typically 30–75 pages). Top-level orchestrator that routes work across five sub-skills — literature-survey, paper-structure-and-logic, experiment-design, academic-figures-and-tables, peer-review-simulation — through phased iteration loops with quality gates and weakness-routing. Target output quality ~8.5/10 reviewer score. Source: https://victorchen96.github.io/auto_research/skill/paper-writing.html
---

# Scientific Paper Writing — Orchestrator (v2.0)

A hierarchical skill group that produces survey-quality papers by routing work across five sub-skills, phased over ~12 iterations, with explicit quality gates and weakness-routing between rounds.

**Sub-skills (invoke each via its own skill):**
- `literature-survey` — recall, score (LQS), classify (A/B/C/D), upgrade arXiv→accepted
- `paper-structure-and-logic` — chapter architecture, paragraph logic, taxonomy, formal claims
- `experiment-design` — pre-registered hypothesis → execute → iterate → JSON report
- `academic-figures-and-tables` — booktabs tables, vector figures, captions that state findings
- `peer-review-simulation` — multi-persona scoring, weakness routing, anti-inflation

**Headline production stats from the framework:** 5 sub-skills, 4 quality gates + 1 blocking final, 3 papers produced averaging 8.5/10.

## Phase routing

### Phase 0 — Topic selection (3-question test)
- **Scope?** Single sub-topic, no overlap with existing surveys.
- **Angle?** What's the unique frame (new taxonomy, new gap, new experiment)?
- **Audience?** Workshop reviewers, main-conference reviewers, or domain practitioners?

### Phase 1 — Draft (iterations 1–6, target 6.0/10)
- Iter 1: [Structure] skeleton + §1–2 + compile end-to-end
- Iter 2: [Literature] Stage 1–2 (recall + LQS scoring)
- Iter 3: [Structure] §3–6 core chapters **||** [Figures] ≥ 2 figures (parallel)
- Iter 4: [Literature] Stage 3–4 (classify + venue upgrade) **||** [Structure] §7–8 (parallel)
- Iter 5: verify citations → compile → [Review] first score
- Iter 6: route fixes from review → compile

### Phase 2 — Deep improvement (iterations 7–9, target 7.5–8.0)
- Iter 7: [Experiment] design + execute pilot
- Iter 8: [Figures] present results + [Structure] integrate experiment narrative
- Iter 9: compile → [Review] → route fixes

### Phase 3 — Sprint (iter 10+, target 8.5+)
Loop: [Review] → weakness routing → fix → compile → [Review]
**Stop** when any of: score ≥ 8.5, OR Δ ≤ 0.3 across two consecutive rounds, OR iter > 12.

## Weakness routing table

Use the reviewer's complaint as the key. Always route to one specific sub-skill.

| Reviewer weakness                 | Route to     | Action                                |
| --------------------------------- | ------------ | ------------------------------------- |
| "Citation coverage insufficient"  | Literature   | Targeted Stage 1–2 search             |
| "Too many arXiv-only refs"        | Literature   | Stage 4 upgrade via DBLP / OpenReview |
| "Missing recent papers"           | Literature   | 2025–2026 focused search              |
| "Structure unclear"               | Structure    | Reorganize + add transitions          |
| "Analysis lacks depth"            | Structure    | Add critical assessment               |
| "Taxonomy not novel"              | Structure    | Redesign multi-axis taxonomy          |
| "Claims too strong"               | Structure    | Hedge-language downgrade              |
| "No experiments"                  | Experiment   | Design pilot study                    |
| "Experiment not rigorous"         | Experiment   | Add trials / ablation                 |
| "Tables incomparable"             | Figures      | Regroup + add Δ column                |
| "Missing visualizations"          | Figures      | Add figure                            |
| "No error bars"                   | Figures      | Add ± std                             |

## Quality gates (1–4 are pre-integration; 5 is blocking)

Each sub-skill's output must pass its gate before integration. Gates 1 & 2 can run in parallel; Gate 5 cannot be skipped.

**Gate 1 — Literature**
- Citations ≥ 80 (draft) / ≥ pages × 3 (final)
- Within 1yr ≥ 40%; Accepted ≥ 30%; arXiv-only ≤ 60%
- Verification rate ≥ 80%
- Every taxonomy cell has ≥ 2 A/B-level references

**Gate 2 — Experiment**
- Pre-registered, clear hypothesis
- Statistical test reported (p-value or CI)
- ≥ 3 trials with std
- No ceiling/floor effect
- Links to a specific paper claim
- (Bonus) surprise finding documented

**Gate 3 — Structure**
- Compiles with 0 errors, 0 undefined refs
- Every `.tex` file ≤ 300 lines
- Abstract–conclusion alignment verified
- Inter-section transitions present
- Critical assessment in every core section
- ≥ 1 formal claim (conjecture / observation)
- Consistent terminology throughout

**Gate 4 — Figures & tables**
- Full survey: tables ≥ 10, figures ≥ 6
- booktabs format, no vertical lines
- Each conveys a non-trivial insight
- Captions state a conclusion, not just a description
- Every figure/table referenced in body text
- Experimental data shown as mean ± std

**Gate 5 — Final review (blocking)**
- Gates 1–4 all passed
- PDF compiles cleanly
- Peer-review score ≥ phase target (6.0 / 7.0 / 8.0 / 8.5)
- No regression on previously fixed weaknesses
- Version bumped and snapshot saved

## Score progression — what each level requires

| Score | Requirements beyond previous                                       | Typical additions                              |
| ----- | ------------------------------------------------------------------ | ---------------------------------------------- |
| 6.0   | Complete draft, 80+ refs, compiles                                 | Full 8 sections + basic tables                 |
| 7.0   | + logical transitions, quantitative data, gap analysis             | Formal conjecture + grouped tables             |
| 8.0   | + original experiment, critical assessment, 150+ refs              | Multi-model pilot study + vector figures       |
| 8.5   | + cross-validation, meta-analysis, key takeaways, proof sketch     | Cross-benchmark table + deeper theory          |

## Production budget guidance

| Sub-skill        | Time % | Score contribution           | Key output                              |
| ---------------- | ------ | ---------------------------- | --------------------------------------- |
| Literature       | 20%    | Foundation (without: ≤ 6.0)  | references.bib + citation_plan.jsonl    |
| Structure        | 35%    | Main driver (6.0 → 7.5)      | full manuscript (sections/*.tex)        |
| Experiment       | 20%    | +1.0–1.5 points              | results.json + experiment_summary.md    |
| Figures & tables | 10%    | +0.5–1.0 points              | figures/*.pdf + tables/*.tex            |
| Review           | 15%    | Drives iteration             | per-round scores + weakness lists       |

## When to invoke

- Drafting a new survey or research paper from scratch.
- Revising an existing paper toward a target reviewer score.
- A user asks for "paper writing", "survey writing", "academic writing pipeline", or names a target like "get this to 8.5".

For a single section, citation cleanup, or a single figure, invoke the relevant sub-skill directly instead of running the full orchestrator.

For long unattended runs (multi-day drafting), pair this with `deli-auto-research` for the orchestration scaffolding.
