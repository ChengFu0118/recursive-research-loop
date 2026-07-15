#!/usr/bin/env python3
"""call-api helper — batched multi-model Claude calls for the paper pipeline.

Two subcommands:
  review     — run reviewer personas x rounds against a draft, collect JSON scores
  experiment — expand a models x conditions x tasks x trials matrix and run it

Credentials come from the environment (ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL);
the zero-arg anthropic.Anthropic() client reads them. No key is ever hardcoded.

Output is append-only JSONL — one line per call, flushed immediately, so a crash
mid-run loses nothing. --resume skips job keys already in the output file.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import anthropic
except ImportError:
    sys.exit("anthropic SDK not installed. Run: pip install anthropic")

DEFAULT_MODEL = "claude-opus-4-8"

# Five reviewer personas (peer-review-simulation). At least one runs on a
# different model than the rest — the anti-inflation diversity rule.
PERSONAS = [
    ("R1_Experimentalist", "claude-opus-4-8",
     "You are R1, an experimentalist reviewer. Judge statistical rigor, baselines, and reproducibility."),
    ("R2_Theorist", "claude-sonnet-5",   # different model → satisfies diversity rule
     "You are R2, a theorist reviewer. Judge formal definitions, MECE taxonomy, and claim calibration."),
    ("R3_Perfectionist", "claude-opus-4-8",
     "You are R3, a perfectionist reviewer. Judge writing quality, figures, and presentation."),
    ("R4_Synthesizer", "claude-opus-4-8",
     "You are R4, a synthesizer reviewer. Judge cross-cutting analysis, gap coverage, and novelty."),
    ("R5_Newcomer", "claude-sonnet-5",
     "You are R5, a newcomer reviewer. Judge accessibility, clarity of definitions, and motivation."),
]

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {
                "soundness": {"type": "number"},
                "clarity": {"type": "number"},
                "novelty": {"type": "number"},
                "significance": {"type": "number"},
            },
            "required": ["soundness", "clarity", "novelty", "significance"],
            "additionalProperties": False,
        },
        "overall": {"type": "number"},
        "top_weakness": {"type": "string"},
    },
    "required": ["scores", "overall", "top_weakness"],
    "additionalProperties": False,
}


def client():
    return anthropic.Anthropic()  # reads env credentials


def _load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["job_key"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def call_once(cli, job_key, model, system, user, structured=False):
    """One API call. Returns a result dict; never raises (errors captured in-row)."""
    t0 = time.time()
    kwargs = dict(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
    )
    if structured:
        kwargs["output_config"]["format"] = {"type": "json_schema", "schema": REVIEW_SCHEMA}
    try:
        resp = cli.messages.create(**kwargs)
        text = next((b.text for b in resp.content if b.type == "text"), "")
        row = {
            "job_key": job_key, "model": model, "ok": True, "text": text,
            "usage": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
            "latency_s": round(time.time() - t0, 2),
        }
        if structured and text:
            try:
                row["parsed"] = json.loads(text)
            except json.JSONDecodeError:
                row["ok"] = False
                row["error"] = "structured output did not parse"
        return row
    except Exception as e:
        return {"job_key": job_key, "model": model, "ok": False,
                "error": str(e), "latency_s": round(time.time() - t0, 2)}


def run_pool(jobs, out_path, concurrency, resume):
    """jobs: list of (job_key, model, system, user, structured). Streams to JSONL."""
    cli = client()
    done = _load_done(out_path) if resume else set()
    jobs = [j for j in jobs if j[0] not in done]
    if not jobs:
        print("# nothing to do (all job keys already present)", file=sys.stderr)
        return
    n_ok = n_err = 0
    with open(out_path, "a") as out, ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {pool.submit(call_once, cli, *j): j[0] for j in jobs}
        for fut in as_completed(futs):
            row = fut.result()
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            if row["ok"]:
                n_ok += 1
            else:
                n_err += 1
                print(f"# ERROR {row['job_key']}: {row.get('error')}", file=sys.stderr)
    print(f"# done: {n_ok} ok, {n_err} errors → {out_path}", file=sys.stderr)


def cmd_review(a):
    draft = open(a.draft, encoding="utf-8").read()
    # Truncate very large drafts to keep the shared context bounded.
    if len(draft) > 120_000:
        draft = draft[:120_000] + "\n...[truncated]..."
    jobs = []
    for rnd in range(1, a.rounds + 1):
        for name, model, persona in PERSONAS:
            user = (
                f"Round {rnd}. Review the following paper draft as {name}.\n\n"
                f"Score each criterion 1-10 and give an overall score and the single "
                f"most important weakness. Be critical; do not inflate.\n\n"
                f"=== DRAFT ===\n{draft}"
            )
            jobs.append((f"review::r{rnd}::{name}", model, persona, user, True))
    run_pool(jobs, a.out, a.concurrency, a.resume)


def cmd_experiment(a):
    spec = json.load(open(a.spec))
    models = spec["models"]
    conditions = spec.get("conditions", [{"name": "default", "system": "", "suffix": ""}])
    tasks = spec["tasks"]  # [{"id": ..., "prompt": ...}, ...]
    trials = spec.get("trials", 1)
    jobs = []
    for model in models:
        for cond in conditions:
            for task in tasks:
                for trial in range(trials):
                    key = f"exp::{model}::{cond['name']}::{task['id']}::t{trial}"
                    user = task["prompt"] + cond.get("suffix", "")
                    jobs.append((key, model, cond.get("system", ""), user, False))
    print(f"# expanded matrix: {len(jobs)} calls "
          f"({len(models)} models x {len(conditions)} conds x {len(tasks)} tasks x {trials} trials)",
          file=sys.stderr)
    run_pool(jobs, a.out, a.concurrency, a.resume)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("review")
    r.add_argument("--draft", required=True)
    r.add_argument("--rounds", type=int, default=1)
    r.add_argument("--out", required=True)
    r.add_argument("--concurrency", type=int, default=8)
    r.add_argument("--resume", action="store_true")
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("experiment")
    e.add_argument("--spec", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--concurrency", type=int, default=8)
    e.add_argument("--resume", action="store_true")
    e.set_defaults(func=cmd_experiment)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
