---
name: paper-structure-and-logic
description: Use when drafting or revising the prose of a scientific paper — chapter architecture, paragraph logic chains, taxonomy design, formal claims, hedge language, abstract-conclusion alignment. Produces sections/*.tex. Main driver of score progression from 6.0 → 7.5. Sub-skill of scientific-paper-writing.
---

# Paper Structure & Logic (Sub-skill 2)

Covers chapter architecture, paragraph logic chains, taxonomy design, formal claims, hedge language, abstract-conclusion alignment.

- **IN:** `references.bib` + experiment findings
- **OUT:** `sections/*.tex` (full manuscript)

## Chapter architecture (survey standard)

- **§1 Introduction** — Hook → Gap → Contributions → Roadmap.
- **§2 Background** — formal definitions, taxonomy overview.
- **§3–6 Core** — one method family per chapter, each with a critical assessment.
- **§7 Benchmarks + Experiments**.
- **§8 Future** — specific open problems formatted as Barrier + Attack vector.
- **§9 Conclusion** — numbered key findings (**not** a paraphrase of the abstract).

## Paragraph logic patterns

| Pattern                | Structure                          | Use case               |
| ---------------------- | ---------------------------------- | ---------------------- |
| Claim-Evidence-Implication | Assert → Data → So what        | Main body              |
| Compare-Contrast       | A → B → Difference → Trade-off     | Method comparison      |
| Concession-Rebuttal    | Admit strength → But limitation    | Critical analysis      |
| Funnel                 | Broad → Narrow → This paper        | Introduction           |

Every body paragraph should map to one of these. Paragraphs that don't are usually weak prose.

## Taxonomy design

- **Multi-axis matrix**, not a flat list.
- **MECE:** mutually exclusive, collectively exhaustive.
- **Empty cells are good** — they fuel gap analysis and motivate future work.
- Methods that span multiple cells reveal taxonomy tension worth discussing.

## Formal claims

- Default to **Conjecture + Remark** (not Theorem) unless you have a proof.
- **Hedge ladder**, strongest → weakest: `demonstrates > suggests > may > hypothesize`.
- Hard rule: **claim strength ≤ evidence strength.** Reviewers downgrade for overclaiming.

## Related-work differentiation

- **Mandatory comparison table** vs. every existing survey on the topic.
- "We're more recent" is **NOT** sufficient differentiation.
- Need structural novelty: new taxonomy, new angle, or new experiment.

## Engineering constraints

- Each `.tex` file ≤ 300 lines (Gate 3).
- Consistent terminology — define once, use exactly that term everywhere.
- Transitions between sections must be explicit (one sentence connecting §N to §N+1).
- Abstract and conclusion must be **independently verified** to claim the same contributions in the same order.

## When to invoke

- Drafting any chapter or §-level prose.
- Reviewer flagged: "structure unclear", "analysis lacks depth", "taxonomy not novel", "claims too strong".
- Before any compile pass after literature or experiment changes (to keep transitions and terminology coherent).
