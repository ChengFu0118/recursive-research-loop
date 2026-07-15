---
name: skill-router
description: Use to decide which skill handles a sub-task when orchestrating multi-step work (literature vs experiment vs figures vs deployment vs search vs API fan-out). The orchestration-layer dispatcher for the paper pipeline and the deli-auto-research loop; invoke when a plan step is described in prose and you need to route it to the right skill, or to see the ranked candidates. Matches a sub-task against every skill's frontmatter description in .claude/skills and returns ranked matches with the exact Skill invocation.
---

# Skill Router (Skill #57)

The orchestration-layer dispatcher. One job: **given a sub-task in prose, pick the skill that should handle it** — so an orchestrator (`scientific-paper-writing`, or a `deli-auto-research` loop) can route work without hardcoding the mapping.

- **IN:** a sub-task description ("upgrade the arXiv-only references", "run the pilot across 3 models")
- **OUT:** ranked skill candidates + the exact `Skill` call to make

## Tooling

A dependency-free matcher reads every `.claude/skills/*/SKILL.md` frontmatter description and scores it against the sub-task by keyword overlap:

```bash
python3 .claude/skills/skill-router/route.py "upgrade the arXiv-only references to accepted venues"
python3 .claude/skills/skill-router/route.py --top 3 "serve the compiled PDF so I can preview it"
python3 .claude/skills/skill-router/route.py --json "run peer review across 5 personas"
```

Output is the best-matching skill name, its score, and a one-line reason (the overlapping terms). Use it as a **hint**, then invoke the chosen skill yourself via the `Skill` tool — the router does not execute skills.

## Routing table (canonical mappings)

The matcher is a ranking aid; these are the intended routes for the paper pipeline:

| Sub-task shape | Route to |
| -------------- | -------- |
| Build/score/classify/upgrade references; "citation coverage", "arXiv-only" | `literature-survey` (retrieval/verify → `search-agent`) |
| Chapter architecture, paragraph logic, taxonomy, claims, hedge language | `paper-structure-and-logic` |
| Pilot study, multi-model API study, GPU RL run, pre-registered hypothesis | `experiment-design` (execution fan-out → `call-api`) |
| Booktabs tables, vector figures, captions, error bars | `academic-figures-and-tables` |
| Score the draft, reviewer personas, weakness routing | `peer-review-simulation` (multi-model scoring → `call-api`) |
| Find/verify a citation, DBLP/OpenReview lookup | `search-agent` |
| Fan out many model calls, compare models, collect rubric scores | `call-api` |
| Host the PDF, generate index.html, restart the preview server | `static-file-service` |
| "run unattended", "keep iterating", stalled/looping autonomous run | `deli-auto-research` |
| Draft/revise a whole paper end-to-end, target a reviewer score | `scientific-paper-writing` (orchestrator) |

## How to use in an orchestration loop

1. Decompose the goal into sub-tasks (the orchestrator's job).
2. For each ambiguous sub-task, run `route.py "<sub-task>"` to get the candidate.
3. Cross-check against the routing table above; the table wins on conflict (the matcher is lexical, not semantic).
4. Invoke the chosen skill with the `Skill` tool, passing the sub-task as `args`.
5. **One level of routing only** — the router picks a leaf skill; it does not recursively route the sub-skill's internal steps (those are that skill's concern).

## Limits

- **Lexical, not semantic.** It matches shared keywords, so paraphrases with no overlapping terms rank low — fall back to the routing table.
- **Reads local skills only.** It scores whatever is under `.claude/skills/`; a skill with a vague description ranks poorly regardless of fit. Keep descriptions keyword-rich (they double as the router's index).
- Ties are broken alphabetically; inspect the top-N (`--top 3`) when the top score is close.

## When to invoke

- An orchestrator (`scientific-paper-writing`, `deli-auto-research`) needs to dispatch a prose sub-task.
- You're unsure which of several overlapping skills owns a step.
- Building a plan and want the skill mapping laid out.

For a single obvious task, skip the router and invoke the skill directly.
