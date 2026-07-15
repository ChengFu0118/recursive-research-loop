---
name: search-agent
description: Use to find and verify academic references — arXiv/Google Scholar search, citation verification, DBLP cross-check, and acceptance-status lookup. The retrieval-and-verification engine behind literature-survey and peer-review; invoke when building a bibliography, confirming a citation is real (title/authors/year/venue), or upgrading an arXiv preprint to its accepted venue. Wraps arXiv + DBLP + OpenReview public APIs (no key required) and falls back to WebSearch/WebFetch.
---

# Search Agent (Skill #5)

The retrieval-and-verification workhorse for the paper pipeline. Two jobs:

1. **Search** — turn a topic/keywords into candidate papers (Literature Stage 1).
2. **Verify** — confirm a citation is real and find its true venue (Literature Stage 4 + Gate-1 verification).

- **IN:** query strings, or a `.bib` / `citation_plan.jsonl` to audit
- **OUT:** candidate list (JSONL) and/or a per-citation verdict (`verified | mismatch | not_found`)

## Tooling

A helper script wraps three **key-free public APIs**:

```bash
python3 .claude/skills/search-agent/search.py search  "quantized llm inference" --max 50
python3 .claude/skills/search-agent/search.py verify  --title "GPTQ: Accurate ..." --author Frantar --year 2023
python3 .claude/skills/search-agent/search.py dblp    "equality saturation"
python3 .claude/skills/search-agent/search.py bib     research/references.bib   # audit a whole .bib
```

- **arXiv API** (`export.arxiv.org/api/query`) — full-text search, returns title/authors/abstract/id/date.
- **DBLP** (`dblp.org/search/publ/api`) — authoritative venue + acceptance status.
- **OpenReview** (`api2.openreview.net`) — review status for ICLR/NeurIPS/etc.

If the script fails (network/rate-limit) or a lookup is ambiguous, **fall back to the `WebSearch` / `WebFetch` tools** — don't silently drop the citation.

## Search workflow (Stage 1 recall)

1. Expand the topic into **≥ 3 query variants per taxonomy cell**: core terms, synonyms, method names.
2. Run `search.py search` per query; dedupe by arXiv id / normalized title.
3. Snowball: for high-impact hits, fetch their reference lists via `WebFetch` on the arXiv/Semantic-Scholar page.
4. Emit candidates as JSONL (one paper per line: `{title, authors, year, arxiv_id, venue, url}`). Hand off to `literature-survey` for LQS scoring.

## Verification workflow (the hard rule)

For **every citation** (batched **every 20**, never deferred to the end):

1. `search.py verify --title ... --author ... --year ...`.
2. Match on: **title** (normalized, ≥ 0.9 similarity), **first-author surname**, **year (± 1)**.
3. Classify:
   - `verified` — all three match on arXiv or DBLP.
   - `mismatch` — found but a field is wrong → correct it in the `.bib`, log the fix.
   - `not_found` — no hit on any source → **treat as hallucinated: hard fail, remove or replace immediately.**
4. **Venue upgrade:** if DBLP shows an accepted venue for an arXiv-only entry, rewrite `@misc`/`@article` → `@inproceedings`.

Target: verification rate ≥ 80%, **hallucinated = 0**.

## When to invoke

- `literature-survey` Stage 1 (recall) or Stage 4 (venue upgrade).
- Any "is this citation real?" / "find the published version" question.
- Gate-1 pre-integration audit of a `.bib` file.
- A reviewer flagged "too many arXiv-only refs" or "missing recent papers".

Do **not** use for scoring/classification (that's `literature-survey`) or for writing prose.
