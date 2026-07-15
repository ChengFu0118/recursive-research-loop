#!/usr/bin/env python3
"""Readiness detector: has research-loop-init completed for this workdir?

The single source of truth is state/trial_report.json, stamped by the init
skill. Readiness is invalidated automatically when experiment.yaml or
.research-loop/executor.sh change after the stamp (hash mismatch) — config
drift means the smoke test must be repeated.

Commands:
  status <workdir>
      Print JSON {ready, phase_needed, reasons}; exit 0 if ready, 1 if not.
      phase_needed is one of: interview | trial | baseline | null
  stamp <workdir> [--trial-passed] [--baseline-measured] [--iteration-sec N]
      Update state/trial_report.json, recomputing config hashes.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

REPORT = "state/trial_report.json"
CONFIG_FILES = ["experiment.yaml", ".research-loop/executor.sh"]


def sha(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def hashes(workdir: str) -> dict:
    return {f: sha(os.path.join(workdir, f)) for f in CONFIG_FILES}


def status(workdir: str) -> dict:
    reasons, phase = [], None
    if not os.path.isfile(os.path.join(workdir, "experiment.yaml")):
        reasons.append("experiment.yaml missing")
        phase = "interview"
    executor = os.path.join(workdir, ".research-loop", "executor.sh")
    if not os.access(executor, os.X_OK):
        reasons.append(".research-loop/executor.sh missing or not executable")
        phase = phase or "interview"

    report_path = os.path.join(workdir, REPORT)
    if not os.path.isfile(report_path):
        reasons.append("no trial_report.json — smoke test never ran")
        phase = phase or "trial"
        return {"ready": False, "phase_needed": phase, "reasons": reasons}

    report = json.load(open(report_path))
    if not report.get("trial_passed"):
        reasons.append("trial not passed")
        phase = phase or "trial"
    if not report.get("baseline_measured"):
        reasons.append("baseline not measured")
        phase = phase or "baseline"
    current = hashes(workdir)
    stamped = report.get("config_hashes", {})
    for f in CONFIG_FILES:
        if current.get(f) != stamped.get(f):
            reasons.append(f"{f} changed since trial — re-run smoke test")
            phase = "trial"
    return {"ready": not reasons, "phase_needed": phase, "reasons": reasons}


def stamp(workdir: str, args: argparse.Namespace) -> dict:
    report_path = os.path.join(workdir, REPORT)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report = json.load(open(report_path)) if os.path.isfile(report_path) else {}
    if args.trial_passed:
        report["trial_passed"] = True
    if args.baseline_measured:
        report["baseline_measured"] = True
    if args.iteration_sec is not None:
        report["iteration_wallclock_sec"] = args.iteration_sec
    report["config_hashes"] = hashes(workdir)
    report["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(report, open(report_path, "w"), indent=2)
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["status", "stamp"])
    p.add_argument("workdir")
    p.add_argument("--trial-passed", action="store_true")
    p.add_argument("--baseline-measured", action="store_true")
    p.add_argument("--iteration-sec", type=float, default=None)
    args = p.parse_args()

    if args.command == "status":
        result = status(args.workdir)
        print(json.dumps(result, indent=2))
        return 0 if result["ready"] else 1
    print(json.dumps(stamp(args.workdir, args), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
