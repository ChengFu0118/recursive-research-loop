---
name: static-file-service
description: Use to publish and serve the paper pipeline's build artifacts — host the compiled PDF, auto-generate an index.html landing page listing papers/figures/logs, and start/stop/restart the static file server. The deploy-phase skill behind the scientific-paper-writing pipeline; invoke when a draft compiles and you want it browsable, or when you need a local preview server for figures and review reports. Pure Python stdlib (http.server) — no dependencies, no external hosting.
---

# Static File Service (Skill #6)

The deploy-phase publisher for the paper pipeline. Three jobs:

1. **PDF hosting** — expose the compiled `main.pdf` (and any figures/logs) over HTTP.
2. **index.html generation** — auto-build a landing page listing the artifacts with sizes and mtimes.
3. **Service lifecycle** — start / stop / restart / status the server on a fixed port.

- **IN:** a root directory of artifacts (default `research/`) + a port
- **OUT:** a running local server + a generated `index.html`

Local-only by design: it binds `127.0.0.1` and serves files you point it at. It does **not** deploy to the public internet — that keeps unreviewed drafts private (see the safety note).

## Tooling

A dependency-free helper wraps `http.server` plus an index generator:

```bash
# Generate index.html listing PDFs / figures / logs under research/
python3 .claude/skills/static-file-service/serve.py index --root research

# Start the server in the background (writes a PID file), then check it
python3 .claude/skills/static-file-service/serve.py start   --root research --port 8123
python3 .claude/skills/static-file-service/serve.py status  --port 8123
curl -sS http://127.0.0.1:8123/ | head

# Restart after a rebuild (regenerates index.html, then bounces the server)
python3 .claude/skills/static-file-service/serve.py restart --root research --port 8123

# Stop when done
python3 .claude/skills/static-file-service/serve.py stop    --port 8123
```

Behaviors:
- **PID file** at `<root>/.static-file-service.<port>.pid` tracks the running server; `start` refuses to double-start, `restart`/`stop` use it.
- **index.html** is regenerated on every `start`/`restart` so it always reflects the latest build.
- Binds `127.0.0.1` only. Use an SSH tunnel if you need remote access — don't bind `0.0.0.0`.

## index.html generation

The generated page groups artifacts by type:
- **Papers** — `*.pdf` (the headline `main.pdf` first).
- **Figures** — `figures/*.pdf`, `figures/*.png`.
- **Logs / reports** — `state/*.md`, `*.jsonl`, review rounds.

Each entry shows filename (linked), size, and last-modified time. Regenerate any time with `serve.py index`.

## Service restart pattern (deploy loop)

After each successful compile in the paper pipeline:

1. `latexmk` / build → `research/main.pdf`.
2. `serve.py restart --root research --port 8123` — regenerates the index and bounces the server.
3. The reviewer/user refreshes `http://127.0.0.1:8123/` to see the new PDF.

This mirrors the framework's "PDF hosting, index.html generation, service restart" deploy step.

## Safety

- **Local-bind only.** The server is for preview, not publication. Never rebind to a public interface to "share" an unreviewed draft — an in-progress paper with unverified citations should not be exposed.
- Serves whatever is under `--root`; point it at the artifacts directory, not `$HOME`.

## When to invoke

- A draft compiled and you want it browsable, or to preview figures/review reports locally.
- The paper pipeline's deploy phase (post-compile).
- You need a quick static server for any build output in this repo.

Not for programmatic file *reads* (use the Read tool) — this is for serving a browsable tree.
