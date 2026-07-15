#!/usr/bin/env python3
"""Training-track payload: run a training command under a wall-clock budget
and parse the metric from its logs. Backend-neutral — the executor decides
where this runs; the training command decides how many devices it uses.

Examples:
  # NanoGPT speedrun (metric = wall-clock seconds to reach target val loss)
  train_and_parse.py --workdir candidates/nanogpt --parse nanogpt --target-loss 3.28 \
      --budget-sec 3000 --seed 0 --cmd "torchrun --nproc_per_node=8 train_gpt.py --seed={seed}"

  # NanoChat budget run (metric = best val BPB within the budget)
  train_and_parse.py --workdir candidates/nanochat --parse nanochat \
      --budget-sec 300 --seed 0 --cmd "python train.py --seed={seed}"

VERIFY: entrypoint names and log formats against the cloned upstream repos
before the first run — both repos evolve quickly.

Prints one line:  RESULT_JSON:{"seed":..,"correct":..,"metric":..,...}
"""

import argparse
import json
import re
import shlex
import subprocess
import time


def parse_nanogpt(log: str, target_loss: float) -> dict:
    # VERIFY: val-loss log format, e.g. "step:1875 ... val_loss:3.2790"
    losses = [float(m.group(1)) for m in re.finditer(r"val_loss:([\d.]+)", log)]
    reached = any(loss <= target_loss for loss in losses)
    return {"correct": reached, "final_val_loss": losses[-1] if losses else None}


def parse_nanochat(log: str, _target: float) -> dict:
    # VERIFY: BPB log format, e.g. "val bpb: 0.9109"
    bpbs = [float(m.group(1)) for m in re.finditer(r"val[_ ]bpb[:= ]\s*([\d.]+)", log)]
    return {"correct": bool(bpbs), "best_bpb": min(bpbs) if bpbs else None}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--cmd", required=True, help="training command; {seed} is substituted")
    p.add_argument("--parse", choices=["nanogpt", "nanochat"], required=True)
    p.add_argument("--budget-sec", type=int, required=True)
    p.add_argument("--target-loss", type=float, default=3.28)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

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

    parsed = (parse_nanogpt if args.parse == "nanogpt" else parse_nanochat)(
        log, args.target_loss
    )
    if args.parse == "nanogpt":
        metric = elapsed if parsed["correct"] else float("inf")
    else:
        metric = parsed["best_bpb"] if parsed["correct"] else float("inf")

    result = {
        "seed": args.seed,
        "wallclock_sec": elapsed,
        "metric": metric,
        **parsed,
        "log_tail": log[-2000:],
    }
    print("RESULT_JSON:" + json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
