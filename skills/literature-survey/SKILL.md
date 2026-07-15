---
name: literature-survey
description: Use when building a paper's reference list, doing a literature review, or fixing citation-coverage / arXiv-ratio / recency weaknesses flagged by reviewers. Four-stage pipeline — Recall → Score (LQS) → Classify (A/B/C/D) → Upgrade (arXiv→accepted) — producing references.bib + citation_plan.jsonl. Sub-skill of scientific-paper-writing.
---

# Literature Survey (Sub-skill 1)

A 4-stage pipeline: **Recall → Score (LQS) → Classify (A/B/C/D) → Upgrade (arXiv→accepted)**.

- **IN:** topic + taxonomy keywords
- **OUT:** `references.bib` + `citation_plan.jsonl`

## Stage 1 — High-recall retrieval

- 20–30 keyword queries via `search.py -o "site:arxiv.org ..."` (or equivalent).
- **≥ 3 query variants per taxonomy cell**: core terms, synonyms, method names.
- Snowball via seed-paper citation networks (follow refs of high-impact papers).
- **Target: 200–500 raw candidates.** Aim wide here — pruning happens in Stage 2.

## Stage 2 — LQS multi-dimensional scoring

Each candidate gets a Literature Quality Score:

| Dimension        | Weight | Scoring                                                    |
| ---------------- | ------ | ---------------------------------------------------------- |
| Recency          | 30%    | 6mo = 10, 1yr = 8, 2yr = 5, 3yr = 3                        |
| Citation impact  | 25%    | cites/month: ≥ 50 = 10, ≥ 10 = 8, ≥ 3 = 6                  |
| Venue            | 20%    | Top-tier = 10, Strong = 7, Workshop = 4                    |
| Institution      | 10%    | Top lab = 10, Top university = 9                           |
| Acceptance       | 15%    | Accepted = 10, Under review = 5, None = 3                  |

**Thresholds:**
- LQS ≥ 7.0 → **must-cite**
- 5.0 ≤ LQS < 7.0 → **conditional** (cite if it fits a gap)
- LQS < 5.0 → **drop**

## Stage 3 — Citation depth classification

Tag every must-cite reference with the depth it deserves:

- **A-level** — 1–3 paragraphs. "Section protagonist." **3–5 per chapter.**
- **B-level** — 2–5 sentences. Important insight. **5–10 per chapter.**
- **C-level** — 1 sentence. Supporting evidence.
- **D-level** — dropped, not cited.

Write the classification into `citation_plan.jsonl` so Structure knows depth per ref.

## Stage 4 — Venue upgrade

- Cross-check **DBLP** + **OpenReview** for acceptance status.
- arXiv tagged "Accepted at X" → rewrite as `@inproceedings`.
- **Target: arXiv-only ratio ≤ 60%.** Above that, reviewers will flag the paper as immature.

## Verification

- **Every 20 citations**, audit: title match, author list, year, venue. Never batch this to the end — fabrications compound.
- Verification rate ≥ 80% of citations independently confirmed.
- **Hallucinated = 0** (any fabricated ref is a hard fail, fix immediately).
- Year distribution: within 1yr ≥ 40%, accepted ≥ 30%.

## When to invoke

- Building a paper's reference list from a topic.
- Reviewer flagged: "citation coverage insufficient", "too many arXiv-only", "missing recent papers".
- Pre-Gate-1 verification before integrating bibliography into a draft.
