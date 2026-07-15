---
name: academic-figures-and-tables
description: Use when producing high-information-density tables and vector figures for an academic paper — booktabs format, captions that state findings, TikZ/matplotlib outputs. Presentation layer for every piece of data in the paper; adds +0.5–1.0 to reviewer score. Sub-skill of scientific-paper-writing.
---

# Academic Figures & Tables (Sub-skill 4)

The presentation layer for every piece of data in the paper. Information density and visual rigor are non-negotiable.

- **IN:** `results.json` + section placeholders
- **OUT:** `figures/*.pdf` + `tables/*.tex`

## Table types

| Type                | Use                          | Info density |
| ------------------- | ---------------------------- | ------------ |
| Comparison matrix   | Methods × features           | Very high    |
| Benchmark table     | Models × metrics             | High         |
| Ablation table      | Conditions × results         | High         |
| Taxonomy table      | Classification visualization | Medium       |
| Meta-analysis       | Aggregated cross-paper data  | Very high    |

## Table rules

- **No vertical lines.** booktabs three-line style only (`\toprule \midrule \bottomrule`).
- Alternating row color: `\rowcolor{gray!6}` for readability.
- **Bold the best result** in each column.
- All experimental data shown as **mean ± std**.
- **Caption must state the key finding**, not just describe the columns. Bad: "Accuracy across models." Good: "Frontier models gain +14% from CoT on math, but lose 3% on commonsense."

## Figure types and tools

| Type                              | Tool                      |
| --------------------------------- | ------------------------- |
| Data-driven (curves, bars, heatmaps) | matplotlib → PDF       |
| Architecture / flow diagrams      | TikZ or SVG → PDF         |
| Simple schematics                 | PIL → PNG (acceptable)    |

**Priority:** TikZ > matplotlib PDF > SVG→PDF > PIL PNG.

## Quality checklist

- Vector format (PDF) preferred; PNG ≥ **300 DPI** if used.
- Font size **≥ 10pt after scaling** — verify by viewing at print size.
- Academic palette: blue `#2196F3`, red `#F44336`, green `#4CAF50`, orange `#FF9800`.
- All axes labeled, all lines in legend.
- Light grid only (`alpha=0.3`).
- **Self-contained** — readable without the main text.

## Quantity targets

- Full survey (50+ pages): **≥ 10 tables, ≥ 6 figures**.
- Short survey (~30 pages): **≥ 5 tables, ≥ 3 figures**.

## Gate 4 — pre-integration checks

- Quantity meets above target for paper length
- booktabs format, no vertical lines
- Each table/figure conveys a non-trivial insight
- Captions state a conclusion, not just a description
- Every figure/table referenced in body text
- Experimental data shown as mean ± std

## When to invoke

- Turning `results.json` into paper-ready visuals.
- Reviewer flagged: "tables incomparable", "missing visualizations", "no error bars", "figures unclear".
- After every experiment run, before the next compile pass.
