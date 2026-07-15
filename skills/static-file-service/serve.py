#!/usr/bin/env python3
"""static-file-service helper — host paper artifacts locally, no dependencies.

Subcommands:
  index   — (re)generate index.html listing PDFs / figures / logs under --root
  start   — generate index, then serve --root on 127.0.0.1:--port (background)
  stop    — stop the server tracked by the PID file
  restart — stop (if running), regenerate index, start again
  status  — report whether the server is up

Binds 127.0.0.1 only — preview, not publication. Use an SSH tunnel for remote
access; never bind 0.0.0.0 to share an unreviewed draft.
"""
import argparse
import datetime as dt
import html
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PID_FMT = ".static-file-service.{port}.pid"


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def collect(root: Path):
    """Group artifacts by kind. Returns dict[label] -> list[Path], main.pdf first."""
    groups = {"Papers": [], "Figures": [], "Logs / reports": []}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name == "index.html" or p.name.startswith("."):
            continue
        rel = p.relative_to(root)
        suf = p.suffix.lower()
        if suf == ".pdf" and "figure" not in str(rel).lower():
            groups["Papers"].append(p)
        elif suf in (".pdf", ".png", ".jpg", ".jpeg", ".svg"):
            groups["Figures"].append(p)
        elif suf in (".md", ".jsonl", ".json", ".log", ".txt"):
            groups["Logs / reports"].append(p)
    # Headline main.pdf first.
    groups["Papers"].sort(key=lambda p: (p.name != "main.pdf", p.name))
    return groups


def gen_index(root: Path) -> Path:
    groups = collect(root)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        "<!doctype html><meta charset=utf-8>",
        "<title>Paper artifacts</title>",
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem}"
        "h1{font-size:1.4rem}h2{margin-top:1.6rem;border-bottom:1px solid #ddd;padding-bottom:.2rem}"
        "table{border-collapse:collapse;width:100%}td{padding:.25rem .6rem}"
        "td.s{color:#666;font-variant-numeric:tabular-nums;white-space:nowrap}"
        "a{text-decoration:none}a:hover{text-decoration:underline}</style>",
        f"<h1>Paper artifacts</h1><p style='color:#666'>Generated {now} — {html.escape(str(root))}</p>",
    ]
    for label, items in groups.items():
        if not items:
            continue
        parts.append(f"<h2>{label}</h2><table>")
        for p in items:
            rel = p.relative_to(root)
            st = p.stat()
            mtime = dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            href = html.escape(str(rel))
            parts.append(
                f"<tr><td><a href='{href}'>{html.escape(str(rel))}</a></td>"
                f"<td class=s>{human_size(st.st_size)}</td><td class=s>{mtime}</td></tr>"
            )
        parts.append("</table>")
    if not any(groups.values()):
        parts.append("<p><em>No artifacts found.</em></p>")
    out = root / "index.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def pid_path(root: Path, port: int) -> Path:
    return root / PID_FMT.format(port=port)


def read_pid(root: Path, port: int):
    pf = pid_path(root, port)
    if not pf.exists():
        return None
    try:
        pid = int(pf.read_text().strip())
    except ValueError:
        return None
    try:
        os.kill(pid, 0)  # signal 0 = liveness probe
        return pid
    except OSError:
        pf.unlink(missing_ok=True)  # stale
        return None


def cmd_index(a):
    out = gen_index(Path(a.root))
    print(f"# wrote {out}", file=sys.stderr)


def cmd_start(a):
    root = Path(a.root).resolve()
    if read_pid(root, a.port):
        sys.exit(f"already running on port {a.port} (see {pid_path(root, a.port)})")
    gen_index(root)
    # Launch a detached http.server bound to loopback.
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(a.port),
         "--bind", "127.0.0.1", "--directory", str(root)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    pid_path(root, a.port).write_text(str(proc.pid))
    time.sleep(0.6)
    if read_pid(root, a.port):
        print(f"# serving {root} at http://127.0.0.1:{a.port}/ (pid {proc.pid})", file=sys.stderr)
    else:
        sys.exit("server failed to start")


def cmd_stop(a):
    root = Path(a.root).resolve()
    pid = read_pid(root, a.port)
    if not pid:
        print(f"# not running on port {a.port}", file=sys.stderr)
        return
    os.kill(pid, signal.SIGTERM)
    pid_path(root, a.port).unlink(missing_ok=True)
    print(f"# stopped pid {pid}", file=sys.stderr)


def cmd_restart(a):
    cmd_stop(a)
    time.sleep(0.3)
    cmd_start(a)


def cmd_status(a):
    root = Path(a.root).resolve()
    pid = read_pid(root, a.port)
    if not pid:
        print(f"down (port {a.port})")
        sys.exit(1)
    try:
        # Bypass any HTTP(S)_PROXY env — loopback must be reached directly.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{a.port}/", timeout=3) as r:
            code = r.status
    except Exception as e:
        print(f"pid {pid} alive but not responding: {e}")
        sys.exit(1)
    print(f"up (pid {pid}, http {code}, http://127.0.0.1:{a.port}/)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, func in [("index", cmd_index), ("start", cmd_start), ("stop", cmd_stop),
                       ("restart", cmd_restart), ("status", cmd_status)]:
        p = sub.add_parser(name)
        p.add_argument("--root", default="research")
        p.add_argument("--port", type=int, default=8123)
        p.set_defaults(func=func)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
