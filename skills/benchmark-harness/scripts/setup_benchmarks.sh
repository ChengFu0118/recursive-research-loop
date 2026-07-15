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

echo "OK: $WORKDIR ready. Next: 'modal token new' if needed, then run a baseline"
echo "measurement for each track and store it in baselines/<track>.json."
