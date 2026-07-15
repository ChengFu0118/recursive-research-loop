"""Modal entrypoints for the three benchmark tracks.

Contracts:
  Kernel track  — problem dir has reference.py defining get_inputs() -> tuple[Tensor,...]
                  and ref(*inputs) -> Tensor; the candidate file defines run(*inputs) -> Tensor.
                  Score = median ref_time / candidate_time; correctness = allclose(rtol=1e-3, atol=1e-3).
  NanoGPT       — candidate dir is a modded-nanogpt working copy; score = wall-clock seconds
                  to reach --target-loss on 8 GPUs.
  NanoChat      — candidate dir is a nanochat working copy; score = validation BPB after a
                  fixed wall-clock budget on 1 GPU.

Every function prints exactly one JSON result line prefixed with RESULT_JSON:
the caller appends it to runs/<track>-<iter>.jsonl.
"""

import json
import subprocess
import time

import modal

app = modal.App("research-loop-harness")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch", "triton", "numpy", "tiktoken", "huggingface_hub")
    .apt_install("git")
)

TIMING_ITERS = 100
WARMUP_ITERS = 20


@app.function(image=image, gpu="H100", timeout=600)
def kernel_eval_remote(reference_src: str, candidate_src: str, seed: int) -> dict:
    import torch

    ref_ns, cand_ns = {}, {}
    exec(reference_src, ref_ns)  # trusted: reference is hook-protected, read-only
    exec(candidate_src, cand_ns)

    torch.manual_seed(seed)
    inputs = tuple(t.cuda() if hasattr(t, "cuda") else t for t in ref_ns["get_inputs"]())

    expected = ref_ns["ref"](*inputs)
    actual = cand_ns["run"](*inputs)
    correct = torch.allclose(expected, actual, rtol=1e-3, atol=1e-3)

    def bench(fn):
        for _ in range(WARMUP_ITERS):
            fn(*inputs)
        torch.cuda.synchronize()
        start, end = torch.cuda.Event(True), torch.cuda.Event(True)
        start.record()
        for _ in range(TIMING_ITERS):
            fn(*inputs)
        end.record()
        torch.cuda.synchronize()
        return start.elapsed_time(end) / TIMING_ITERS

    ref_ms = bench(ref_ns["ref"])
    cand_ms = bench(cand_ns["run"]) if correct else float("inf")
    return {
        "seed": seed,
        "correct": bool(correct),
        "ref_ms": ref_ms,
        "candidate_ms": cand_ms,
        "speedup": ref_ms / cand_ms if correct else 0.0,
    }


@app.local_entrypoint()
def kernel_eval(problem_dir: str, candidate: str, seeds: int = 3):
    reference_src = open(f"{problem_dir}/reference.py").read()
    candidate_src = open(candidate).read()
    for seed in range(seeds):
        result = kernel_eval_remote.remote(reference_src, candidate_src, seed)
        result["metric"] = result["speedup"]
        print("RESULT_JSON:" + json.dumps(result))


def _run_training(candidate_dir: str, cmd: list[str], budget_sec: int) -> tuple[str, float]:
    """Run a training command in the candidate dir with a hard wall-clock cap."""
    t0 = time.monotonic()
    proc = subprocess.run(
        cmd, cwd=candidate_dir, capture_output=True, text=True, timeout=budget_sec
    )
    return proc.stdout + proc.stderr, time.monotonic() - t0


@app.function(image=image, gpu="H100:8", timeout=3600)
def nanogpt_remote(candidate_files: dict, target_loss: float, seed: int) -> dict:
    import os
    import re

    workdir = "/root/candidate"
    os.makedirs(workdir, exist_ok=True)
    for rel, content in candidate_files.items():
        path = os.path.join(workdir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(content)

    # VERIFY: entrypoint + data download step against the modded-nanogpt README
    # (the speedrun repo ships run.sh / train_gpt.py and a data fetch script).
    log, elapsed = _run_training(
        workdir,
        ["torchrun", "--nproc_per_node=8", "train_gpt.py", f"--seed={seed}"],
        budget_sec=3000,
    )
    # VERIFY: val-loss log format, e.g. "val_loss:3.2790 ..."
    losses = [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"step:(\d+).*?val_loss:([\d.]+)", log)
    ]
    reached = [t for t, loss in losses if loss <= target_loss]
    return {
        "seed": seed,
        "correct": bool(reached),
        "wallclock_sec": elapsed,
        "final_val_loss": losses[-1][1] if losses else None,
        "metric": elapsed if reached else float("inf"),
        "log_tail": log[-2000:],
    }


@app.local_entrypoint()
def nanogpt_speedrun(candidate_dir: str, target_loss: float = 3.28, seeds: int = 1):
    files = _collect_py(candidate_dir)
    for seed in range(seeds):
        print("RESULT_JSON:" + json.dumps(nanogpt_remote.remote(files, target_loss, seed)))


@app.function(image=image, gpu="H100", timeout=900)
def nanochat_remote(candidate_files: dict, budget_sec: int, seed: int) -> dict:
    import os
    import re

    workdir = "/root/candidate"
    os.makedirs(workdir, exist_ok=True)
    for rel, content in candidate_files.items():
        path = os.path.join(workdir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(content)

    # VERIFY: training entrypoint and BPB log format against the nanochat README.
    try:
        log, elapsed = _run_training(
            workdir, ["python", "train.py", f"--seed={seed}"], budget_sec=budget_sec
        )
    except subprocess.TimeoutExpired as exc:
        log, elapsed = (exc.stdout or "") + (exc.stderr or ""), budget_sec
    bpbs = [float(m.group(1)) for m in re.finditer(r"val[_ ]bpb[:= ]([\d.]+)", log)]
    return {
        "seed": seed,
        "correct": bool(bpbs),
        "wallclock_sec": elapsed,
        "metric": min(bpbs) if bpbs else float("inf"),
        "log_tail": log[-2000:],
    }


@app.local_entrypoint()
def nanochat_budget(candidate_dir: str, budget_sec: int = 300, seeds: int = 3):
    files = _collect_py(candidate_dir)
    for seed in range(seeds):
        print("RESULT_JSON:" + json.dumps(nanochat_remote.remote(files, budget_sec, seed)))


def _collect_py(candidate_dir: str) -> dict:
    import os

    files = {}
    for root, _, names in os.walk(candidate_dir):
        for name in names:
            if name.endswith((".py", ".sh", ".txt", ".yaml", ".yml", ".json")):
                path = os.path.join(root, name)
                files[os.path.relpath(path, candidate_dir)] = open(path).read()
    return files
