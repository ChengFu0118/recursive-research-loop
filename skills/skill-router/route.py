#!/usr/bin/env python3
"""skill-router helper — match a prose sub-task to the right local skill.

Reads every .claude/skills/*/SKILL.md frontmatter `description:` and scores it
against the sub-task by keyword overlap (lexical, not semantic). Prints ranked
candidates and the exact Skill invocation to make. It does NOT execute skills.

Usage:
  route.py "upgrade the arXiv-only references"
  route.py --top 3 "serve the compiled PDF"
  route.py --json "run peer review across 5 personas"
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Light stopword list so common words don't dominate the overlap score.
STOP = set("""a an the of to and or for in on with is are be this that these those
your you i it as at by from into over under run use using make get set new all any
via per each need needs want when where which what who how do does done step task
sub subtask skill paper draft it's its also then than so if not no yes will can may""".split())


def skills_root():
    # Resolve .claude/skills relative to this file: <root>/.claude/skills/skill-router/route.py
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "skill-router"
        if cand == here.parent:
            return here.parent.parent  # the skills/ dir
    return here.parent.parent


def tokenize(text):
    toks = re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower())
    return {t for t in toks if t not in STOP and len(t) > 2}


def load_skills(root: Path):
    skills = []
    for sk in sorted(root.glob("*/SKILL.md")):
        name = sk.parent.name
        if name == "skill-router":
            continue  # don't route to the router itself
        text = sk.read_text(encoding="utf-8")
        m = re.search(r"^description:\s*(.+?)(?:\n[a-z_]+:|\n---)", text, re.S | re.M)
        desc = " ".join(m.group(1).split()) if m else ""
        skills.append((name, desc, tokenize(desc + " " + name.replace("-", " "))))
    return skills


def rank(task, skills):
    q = tokenize(task)
    scored = []
    for name, desc, toks in skills:
        overlap = q & toks
        # Score = overlap size, normalized lightly by description breadth so a
        # very long description doesn't win purely by having more words.
        score = len(overlap) / (1 + 0.02 * len(toks))
        scored.append((round(score, 3), name, desc, sorted(overlap)))
    # Highest score first; ties broken alphabetically by name.
    scored.sort(key=lambda r: (-r[0], r[1]))
    return scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", help="the sub-task description to route")
    ap.add_argument("--top", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    skills = load_skills(skills_root())
    if not skills:
        sys.exit("no skills found under .claude/skills/")
    ranked = rank(a.task, skills)[: max(1, a.top)]

    if a.json:
        print(json.dumps(
            [{"skill": n, "score": s, "matched_terms": t, "description": d}
             for s, n, d, t in ranked],
            ensure_ascii=False, indent=2))
        return

    best = ranked[0]
    if best[0] == 0:
        print("# no keyword overlap — fall back to the routing table in SKILL.md", file=sys.stderr)
    for i, (score, name, desc, terms) in enumerate(ranked):
        marker = "→" if i == 0 else " "
        reason = ", ".join(terms) if terms else "(no overlap)"
        print(f"{marker} {name}  [score {score}]  match: {reason}")
    print(f"\nInvoke:  Skill(skill=\"{best[1]}\", args=\"{a.task}\")")


if __name__ == "__main__":
    main()
