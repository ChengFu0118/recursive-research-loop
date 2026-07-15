#!/usr/bin/env python3
r"""Generic experiment payload: run a command under a wall-clock budget and
extract the metric from its logs. Backend-neutral — the executor decides where
this runs; the command decides how many devices it uses.

Modes:
  best            metric = best regex-matched value in the log (per --direction)
  time-to-target  metric = wall-clock seconds until a matched value reaches
                  --target (per --direction); inf if never reached

Examples:
  run_and_parse.py --workdir candidates/my-exp --budget-sec 600 --seed 0 \
      --cmd "python train.py --seed={seed}" --metric-regex "val_loss:([\d.]+)" \
      --direction min --mode best

  run_and_parse.py --workdir candidates/my-exp --budget-sec 3000 --seed 0 \
      --cmd "torchrun --nproc_per_node=8 train.py --seed={seed}" \
      --metric-regex "val_loss:([\d.]+)" --direction min \
      --mode time-to-target --target 3.28

The regex's group 1 must capture the numeric value; it is matched against the
combined stdout+stderr of the run. Verify it during research-loop-init's smoke
test — never guess it mid-loop.

Prints one line:  RESULT_JSON:{"seed":..,"correct":..,"metric":..,...}
"""

import argparse
import json
import re
import shlex
import subprocess
import time


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--cmd", required=True, help="run command; {seed} is substituted")
    p.add_argument("--metric-regex", required=True,
                   help="regex with group 1 = metric value, applied to run logs")
    p.add_argument("--direction", choices=["min", "max"], required=True)
    p.add_argument("--mode", choices=["best", "time-to-target"], default="best")
    p.add_argument("--target", type=float, default=None,
                   help="required for mode=time-to-target")
    p.add_argument("--budget-sec", type=int, required=True)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    if args.mode == "time-to-target" and args.target is None:
        p.error("--target is required for mode=time-to-target")

    cmd = shlex.split(args.cmd.format(seed=args.seed))
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=args.workdir, capture_output=True, text=True, timeout=args.budget_sec
        )
        log = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        log = (exc.stdout or "") + (exc.stderr or "")
    elapsed = time.monotonic() - t0

    values = [float(m.group(1)) for m in re.finditer(args.metric_regex, log)]
    best = (min if args.direction == "min" else max)(values) if values else None

    if args.mode == "best":
        correct = bool(values)
        metric = best if best is not None else float("inf")
    else:
        reached = best is not None and (
            best <= args.target if args.direction == "min" else best >= args.target
        )
        correct = reached
        metric = elapsed if reached else float("inf")

    result = {
        "seed": args.seed,
        "correct": correct,
        "metric": metric,
        "best_value": best,
        "n_matches": len(values),
        "wallclock_sec": elapsed,
        "log_tail": log[-2000:],
    }
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
