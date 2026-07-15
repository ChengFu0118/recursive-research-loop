#!/usr/bin/env python3
"""Speedup payload: correctness vs a reference implementation + timed speedup.

For any function-vs-reference experiment — GPU kernels, data transforms, any
drop-in replacement where the candidate must produce the same output faster.

Backend-neutral: runs wherever python3 + torch exist (local CPU, local GPU,
a GKE pod, a Modal function, ...). The executor's only job is to run this
script in that environment and stream its stdout back.

Contract:
  reference.py defines  get_inputs() -> tuple[Tensor,...]  and  ref(*inputs) -> Tensor
  candidate file defines  run(*inputs) -> Tensor

Prints one line per seed:  RESULT_JSON:{"seed":..,"correct":..,"speedup":..,"metric":..}
"""

import argparse
import json
import time

TIMING_ITERS = 100
WARMUP_ITERS = 20


def load_module(path: str) -> dict:
    ns: dict = {}
    exec(open(path).read(), ns)
    return ns


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reference", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--seeds", type=int, default=3)
    args = p.parse_args()

    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    ref_ns = load_module(args.reference)  # reference is hook-protected, read-only
    cand_ns = load_module(args.candidate)

    def bench(fn, inputs) -> float:
        for _ in range(WARMUP_ITERS):
            fn(*inputs)
        if device == "cuda":
            torch.cuda.synchronize()
            start, end = torch.cuda.Event(True), torch.cuda.Event(True)
            start.record()
            for _ in range(TIMING_ITERS):
                fn(*inputs)
            end.record()
            torch.cuda.synchronize()
            return start.elapsed_time(end) / TIMING_ITERS
        t0 = time.perf_counter()
        for _ in range(TIMING_ITERS):
            fn(*inputs)
        return (time.perf_counter() - t0) * 1000 / TIMING_ITERS

    for seed in range(args.seeds):
        torch.manual_seed(seed)
        inputs = tuple(
            t.to(device) if hasattr(t, "to") else t for t in ref_ns["get_inputs"]()
        )
        expected = ref_ns["ref"](*inputs)
        actual = cand_ns["run"](*inputs)
        correct = bool(torch.allclose(expected, actual, rtol=1e-3, atol=1e-3))
        ref_ms = bench(ref_ns["ref"], inputs)
        cand_ms = bench(cand_ns["run"], inputs) if correct else float("inf")
        speedup = ref_ms / cand_ms if correct else 0.0
        print(
            "RESULT_JSON:"
            + json.dumps(
                {
                    "seed": seed,
                    "device": device,
                    "correct": correct,
                    "ref_ms": ref_ms,
                    "candidate_ms": cand_ms,
                    "speedup": speedup,
                    "metric": speedup,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
