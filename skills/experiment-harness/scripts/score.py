#!/usr/bin/env python3
"""Aggregate multi-seed run results and decide whether a candidate improved on baseline.

Usage:
  score.py --runs runs/kernels-17.jsonl --baseline baselines/kernels.json \
           --metric speedup --direction max [--out result.json]

Promotion rules (hard-coded on purpose — do not relax):
  - fewer than 3 seeds            -> improved=false
  - any run with correct=false    -> improved=false
  - |delta| <= max(1% of baseline, 1 std of candidate runs) -> improved=false (noise)
Baseline file schema: {"metric": str, "mean": float, "std": float, "n_seeds": int, ...}
"""

import argparse
import json
import statistics
import sys

MIN_SEEDS = 3
MIN_REL_DELTA = 0.01


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--metric", default="metric")
    p.add_argument("--direction", choices=["min", "max"], required=True)
    p.add_argument("--out", default="result.json")
    args = p.parse_args()

    runs = [json.loads(ln) for ln in open(args.runs) if ln.strip()]
    values = [r[args.metric] for r in runs]
    all_correct = all(r.get("correct", False) for r in runs)
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0

    try:
        baseline = json.load(open(args.baseline))
        baseline_mean = baseline["mean"]
    except FileNotFoundError:
        baseline, baseline_mean = None, None  # first measurement becomes the baseline

    if baseline_mean is None:
        delta, improved, reason = None, False, "no baseline yet — store this as baseline"
    else:
        delta = mean - baseline_mean
        gain = -delta if args.direction == "min" else delta
        threshold = max(MIN_REL_DELTA * abs(baseline_mean), std)
        if len(runs) < MIN_SEEDS:
            improved, reason = False, f"only {len(runs)} seeds (need {MIN_SEEDS})"
        elif not all_correct:
            improved, reason = False, "at least one run failed correctness"
        elif gain <= threshold:
            improved, reason = False, f"gain {gain:.4g} <= noise threshold {threshold:.4g}"
        else:
            improved, reason = True, f"gain {gain:.4g} > threshold {threshold:.4g}"

    result = {
        "metric": args.metric,
        "direction": args.direction,
        "mean": mean,
        "std": std,
        "n_seeds": len(runs),
        "all_correct": all_correct,
        "baseline_mean": baseline_mean,
        "delta": delta,
        "improved": improved,
        "reason": reason,
    }
    json.dump(result, open(args.out, "w"), indent=2)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
