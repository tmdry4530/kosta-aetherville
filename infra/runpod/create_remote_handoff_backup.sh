#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

ENV_FILE="infra/runpod/.env.runpod"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${RUNPOD_HOST:?RUNPOD_HOST is required}"
: "${RUNPOD_SSH_PORT:=22}"
: "${RUNPOD_USER:=root}"
: "${RUNPOD_SSH_KEY:?RUNPOD_SSH_KEY is required}"
: "${RUNPOD_REMOTE_DIR:=/workspace/aetherville}"

REMOTE_RUN_DIR="${AETHERVILLE_RUN_DIR:-/tmp/aetherville}"
STAMP="$(TZ=Asia/Seoul date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="${AETHERVILLE_HANDOFF_BACKUP_ROOT:-.omx/backups}"
BACKUP_DIR="$BACKUP_ROOT/runpod-remote-handoff-$STAMP"
ARCHIVE="$BACKUP_DIR/runpod-remote-workspace-$STAMP.tar.gz"
MANIFEST="$BACKUP_DIR/manifest.txt"
REMOTE_MANIFEST="$BACKUP_DIR/remote-readonly-manifest.txt"
mkdir -p "$BACKUP_DIR"

SSH_OPTS=(-i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)
TARGET="$RUNPOD_USER@$RUNPOD_HOST"

redact_output() {
  local line
  while IFS= read -r line; do
    line="${line//$RUNPOD_HOST/<runpod-host>}"
    line="${line//$RUNPOD_SSH_KEY/<ssh-key>}"
    printf '%s\n' "$line"
  done
}

q_remote_dir=$(printf '%q' "$RUNPOD_REMOTE_DIR")
q_run_dir=$(printf '%q' "$REMOTE_RUN_DIR")
remote_env="RUNPOD_REMOTE_DIR=$q_remote_dir AETHERVILLE_RUN_DIR=$q_run_dir"

cat > "$MANIFEST" <<EOF_MANIFEST
Project Aetherville remote handoff backup
created_at: $STAMP Asia/Seoul
local_branch: $(git branch --show-current 2>/dev/null || echo unknown)
local_head: $(git rev-parse HEAD 2>/dev/null || echo unknown)
remote_workspace: <redacted-target>:$RUNPOD_REMOTE_DIR
remote_run_dir: $REMOTE_RUN_DIR

Includes: remote workspace and runtime learning_state.json when present.
Excludes: .git, .omx, dependency/build/cache folders, model caches, env files, keys, media, large model weights.
Purpose: fast migration safety net before stopping the current RunPod pod.
EOF_MANIFEST

printf '%s\n' "== Capturing read-only remote manifest =="
set +e
ssh "${SSH_OPTS[@]}" "$TARGET" "$remote_env bash -s" >"$REMOTE_MANIFEST" 2>"$BACKUP_DIR/remote-manifest.stderr" <<'REMOTE'
set -euo pipefail
echo "hostname=$(hostname)"
echo "user=$(whoami)"
echo "pwd=$(pwd)"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
else
  echo "nvidia-smi=missing"
fi
python --version || true
node --version || true
pnpm --version || true
uv --version || true
if [ -d "$RUNPOD_REMOTE_DIR" ]; then
  echo "workspace=present"
  du -sh "$RUNPOD_REMOTE_DIR" 2>/dev/null || true
  find "$RUNPOD_REMOTE_DIR" -maxdepth 2 -type f \
    ! -path '*/.env' ! -path '*/.env.*' ! -path '*/infra/runpod/.env.runpod' \
    | sed "s#^$RUNPOD_REMOTE_DIR#.#" | sort | head -200
else
  echo "workspace=missing"
fi
if [ -f "$AETHERVILLE_RUN_DIR/learning_state.json" ]; then
  echo "learning_state=present"
  sha256sum "$AETHERVILLE_RUN_DIR/learning_state.json" || true
else
  echo "learning_state=missing"
fi
ps -eo pid=,comm= | awk '$2 ~ /^(python|uvicorn|vllm|redis-server|caddy)$/ {print}' || true
REMOTE
manifest_status=$?
set -e
cat "$BACKUP_DIR/remote-manifest.stderr" | redact_output >&2
if [[ "$manifest_status" != "0" ]]; then
  echo "Blocker: failed to capture remote manifest." >&2
  exit "$manifest_status"
fi

printf '%s\n' "== Capturing remote workspace tarball =="
set +e
ssh "${SSH_OPTS[@]}" "$TARGET" "$remote_env bash -s" >"$ARCHIVE" 2>"$BACKUP_DIR/remote-tar.stderr" <<'REMOTE'
set -euo pipefail
cd /
paths=()
if [ -d "$RUNPOD_REMOTE_DIR" ]; then
  paths+=("${RUNPOD_REMOTE_DIR#/}")
fi
if [ -f "$AETHERVILLE_RUN_DIR/learning_state.json" ]; then
  paths+=("${AETHERVILLE_RUN_DIR#/}/learning_state.json")
fi
if [ "${#paths[@]}" -eq 0 ]; then
  echo "No remote workspace or learning state found to archive." >&2
  exit 4
fi
tar --ignore-failed-read --warning=no-file-changed \
  --exclude='*/.git' \
  --exclude='*/.omx' \
  --exclude='*/node_modules' \
  --exclude='*/.venv' \
  --exclude='*/client/.next' \
  --exclude='*/dist' \
  --exclude='*/build' \
  --exclude='*/.gstack' \
  --exclude='*/dogfood-output' \
  --exclude='*/__pycache__' \
  --exclude='*/.mypy_cache' \
  --exclude='*/.pytest_cache' \
  --exclude='*/.ruff_cache' \
  --exclude='*/.env' \
  --exclude='*/.env.*' \
  --exclude='*/infra/runpod/.env.runpod' \
  --exclude='*/aetherville-model-cache' \
  --exclude='*/models' \
  --exclude='*.mp4' \
  --exclude='*.mov' \
  --exclude='*.safetensors' \
  --exclude='*.bin' \
  --exclude='*.gguf' \
  --exclude='*.pt' \
  -czf - "${paths[@]}"
REMOTE
tar_status=$?
set -e
cat "$BACKUP_DIR/remote-tar.stderr" | redact_output >&2
if [[ "$tar_status" != "0" ]]; then
  echo "Blocker: remote tar backup failed." >&2
  exit "$tar_status"
fi

(
  sha256sum "$ARCHIVE"
  sha256sum "$MANIFEST"
  sha256sum "$REMOTE_MANIFEST"
) > "$BACKUP_DIR/SHA256SUMS"
sha256sum -c "$BACKUP_DIR/SHA256SUMS"

printf '%s\n' "== Secret-like path scan =="
if tar -tzf "$ARCHIVE" | grep -Ei '(^|/)\.env(\.|$)|env\.runpod|id_ed25519|id_rsa|\.pem$|\.key$' | grep -Ev '(^|/)\.env\.example$|(^|/)\.env\.runpod\.example$' >"$BACKUP_DIR/secret-path-scan.txt"; then
  cat "$BACKUP_DIR/secret-path-scan.txt" >&2
  echo "Blocker: backup contains secret-like paths." >&2
  exit 5
fi
echo "PASS no secret-like paths found beyond allowed examples"

printf '%s\n' "Remote handoff backup complete."
printf '%s\n' "backup_dir=$BACKUP_DIR"
printf '%s\n' "archive=$ARCHIVE"
printf '%s\n' "manifest=$MANIFEST"
