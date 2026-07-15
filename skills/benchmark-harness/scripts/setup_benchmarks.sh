#!/usr/bin/env bash
# Set up benchmark checkouts and candidate working copies in a workdir.
# Usage: setup_benchmarks.sh <workdir>
set -euo pipefail

WORKDIR="${1:?usage: setup_benchmarks.sh <workdir>}"
mkdir -p "$WORKDIR"/{benchmarks,candidates,baselines,runs,state,.research-loop}
cd "$WORKDIR"

clone() { # clone <url> <dest> (skip if present)
  [ -d "$2/.git" ] || git clone --depth 1 "$1" "$2"
}

clone https://github.com/KellerJordan/modded-nanogpt.git benchmarks/modded-nanogpt
clone https://github.com/karpathy/nanochat.git           benchmarks/nanochat
mkdir -p benchmarks/kernels

# Editable working copies — the ONLY place the work agent edits.
[ -d candidates/nanogpt ]  || cp -R benchmarks/modded-nanogpt candidates/nanogpt
[ -d candidates/nanochat ] || cp -R benchmarks/nanochat       candidates/nanochat
mkdir -p candidates/kernels
rm -rf candidates/nanogpt/.git candidates/nanochat/.git

# Extend the plugin's eval-protection hook to the entire benchmarks/ tree:
# candidates/ is the editable surface, benchmarks/ is the immutable reference.
cat > .research-loop/protected-paths.txt <<'EOF'
(^|/)benchmarks/
(^|/)baselines/
(^|/)runs/
EOF

# Default executor = local python3. The user owns this file — replace it to
# target other compute (see executors/gke.sh.example, modal.py.example).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f .research-loop/executor.sh ]; then
  cp "$SCRIPT_DIR/executors/local.sh" .research-loop/executor.sh
  chmod +x .research-loop/executor.sh
fi

echo "OK: $WORKDIR ready."
echo "NEXT (user decision): review .research-loop/executor.sh — it defaults to"
echo "local python3 (CPU/GPU). Replace it to run on your own compute (GKE, Modal,"
echo "SSH, ...); templates in $SCRIPT_DIR/executors/. Then measure a baseline per"
echo "track into baselines/<track>.json."
