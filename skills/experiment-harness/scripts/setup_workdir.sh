#!/usr/bin/env bash
# Create a research-loop workdir skeleton, optionally seeded from the
# experiment's git repo.
#
# Usage: setup_workdir.sh <workdir> [<git-url> <name>]
#   <git-url> <name>  clone the experiment into reference/<name> (read-only)
#                     and copy it to candidates/<name> (the editable surface)
set -euo pipefail

WORKDIR="${1:?usage: setup_workdir.sh <workdir> [<git-url> <name>]}"
REPO="${2:-}"
NAME="${3:-experiment}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$WORKDIR"/{reference,candidates,baselines,runs,state,.research-loop}
cd "$WORKDIR"

if [ -n "$REPO" ]; then
  [ -d "reference/$NAME/.git" ] || git clone --depth 1 "$REPO" "reference/$NAME"
  if [ ! -d "candidates/$NAME" ]; then
    cp -R "reference/$NAME" "candidates/$NAME"
    rm -rf "candidates/$NAME/.git"
  fi
fi

# Extend the plugin's eval-protection hook: candidates/ is the editable
# surface; the reference checkout, baselines, and raw runs are immutable.
cat > .research-loop/protected-paths.txt <<'EOF'
(^|/)reference/
(^|/)baselines/
(^|/)runs/
EOF

# Default executor = local python3. The user owns this file — replace it to
# target other compute (see executors/gke.sh.example, modal.py.example).
if [ ! -f .research-loop/executor.sh ]; then
  cp "$SCRIPT_DIR/executors/local.sh" .research-loop/executor.sh
  chmod +x .research-loop/executor.sh
fi

echo "OK: $WORKDIR ready."
echo "NEXT (user decision): review .research-loop/executor.sh — it defaults to"
echo "local python3. Replace it to run on your own compute (GKE, Modal, SSH, ...);"
echo "templates in $SCRIPT_DIR/executors/. Then run research-loop-init to define"
echo "experiment.yaml, smoke-test the executor, and measure the baseline."
