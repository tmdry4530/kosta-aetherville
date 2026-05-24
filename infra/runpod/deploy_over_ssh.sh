#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
DEPLOY_MODE="${AETHERVILLE_DEPLOY_MODE:-bootstrap}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --mode)
      DEPLOY_MODE="${2:?--mode requires bootstrap|sync-only|direct}"
      shift 2
      ;;
    --mode=*)
      DEPLOY_MODE="${1#--mode=}"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$DEPLOY_MODE" in
  bootstrap|sync-only|direct) ;;
  compose)
    echo "Invalid deploy mode: compose is disabled by the current direct-process runtime policy." >&2
    echo "Docker Compose artifacts are retained only as future portability documentation." >&2
    exit 2
    ;;
  *)
    echo "Invalid deploy mode: $DEPLOY_MODE" >&2
    exit 2
    ;;
esac

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

SSH_OPTS=(-i "$RUNPOD_SSH_KEY" -p "$RUNPOD_SSH_PORT" -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)
TARGET="$RUNPOD_USER@$RUNPOD_HOST"
REDACTED_TARGET="$RUNPOD_USER@<runpod-host>:<port>"

redact_output() {
  local line
  while IFS= read -r line; do
    line="${line//$RUNPOD_HOST/<runpod-host>}"
    line="${line//$RUNPOD_SSH_KEY/<ssh-key>}"
    printf '%s\n' "$line"
  done
}

ssh_capture() {
  local output
  local status
  local restore_errexit=0
  case $- in
    *e*) restore_errexit=1 ;;
  esac
  set +e
  output=$(ssh "${SSH_OPTS[@]}" "$TARGET" "$@" 2>&1)
  status=$?
  if [[ "$restore_errexit" == "1" ]]; then
    set -e
  fi
  printf '%s\n' "$output" | redact_output
  return "$status"
}

EXCLUDES=(
  --exclude .git
  --exclude node_modules
  --exclude .next
  --exclude dist
  --exclude build
  --exclude .venv
  --exclude .gstack
  --exclude dogfood-output
  --exclude __pycache__
  --exclude .env
  --exclude .env.local
  --exclude .env.development
  --exclude .env.production
  --exclude .env.test
  --exclude .env.runpod
  --exclude infra/runpod/.env.runpod
  --exclude models
  --exclude data/raw
)

TAR_EXCLUDES=(
  --exclude=.git
  --exclude=node_modules
  --exclude=.next
  --exclude=dist
  --exclude=build
  --exclude=.venv
  --exclude=.gstack
  --exclude=dogfood-output
  --exclude=__pycache__
  --exclude=.env
  --exclude=.env.local
  --exclude=.env.development
  --exclude=.env.production
  --exclude=.env.test
  --exclude=.env.runpod
  --exclude=infra/runpod/.env.runpod
  --exclude=models
  --exclude=data/raw
)

sync_repository() {
  if ssh_capture "command -v rsync >/dev/null 2>&1" >/tmp/aetherville_remote_rsync_check 2>&1; then
    cat /tmp/aetherville_remote_rsync_check
    set +e
    rsync_output=$(rsync -az --delete "${EXCLUDES[@]}" ./ "$TARGET:$RUNPOD_REMOTE_DIR/" -e "ssh -i $RUNPOD_SSH_KEY -p $RUNPOD_SSH_PORT -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" 2>&1)
    rsync_status=$?
    set -e
    printf '%s\n' "$rsync_output" | redact_output
    return "$rsync_status"
  fi

  cat /tmp/aetherville_remote_rsync_check || true
  echo "Remote rsync is unavailable; using tar-over-ssh sync fallback without delete semantics."
  set +e
  tar_output=$(tar "${TAR_EXCLUDES[@]}" -czf - . 2>&1 | ssh "${SSH_OPTS[@]}" "$TARGET" "mkdir -p '$RUNPOD_REMOTE_DIR' && tar -xzf - -C '$RUNPOD_REMOTE_DIR'" 2>&1)
  tar_status=$?
  set -e
  printf '%s\n' "$tar_output" | redact_output
  return "$tar_status"
}

echo "== Dry run: $DRY_RUN =="
echo "== Deploy mode: $DEPLOY_MODE =="
echo "Target: $REDACTED_TARGET/<remote-dir>"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Would create remote dir, rsync repository, then run mode '$DEPLOY_MODE'."
  if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync not found locally; install rsync before deployment."
    exit 3
  fi
  set +e
  ssh_capture "test -d '$RUNPOD_REMOTE_DIR'"
  workspace_status=$?
  set -e
  if [[ "$workspace_status" == "0" ]]; then
    if ssh_capture "command -v rsync >/dev/null 2>&1" >/tmp/aetherville_remote_rsync_check 2>&1; then
      cat /tmp/aetherville_remote_rsync_check
      set +e
      rsync_output=$(rsync -azn --delete "${EXCLUDES[@]}" ./ "$TARGET:$RUNPOD_REMOTE_DIR/" -e "ssh -i $RUNPOD_SSH_KEY -p $RUNPOD_SSH_PORT -o BatchMode=yes -o ConnectTimeout=15 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" 2>&1)
      rsync_status=$?
      set -e
      printf '%s\n' "$rsync_output" | redact_output
      if [[ "$rsync_status" != "0" ]]; then
        exit "$rsync_status"
      fi
    else
      cat /tmp/aetherville_remote_rsync_check || true
      echo "Remote dir exists but remote rsync is unavailable; dry-run tar-over-ssh sync has no file diff."
    fi
  elif [[ "$workspace_status" == "1" ]]; then
    echo "Remote dir is absent; actual deploy would create it before rsync."
    echo "Dry-run repository sync skipped until the remote dir exists."
  else
    echo "SSH check failed during dry-run; fix credentials or RunPod SSH settings before deploy."
    exit "$workspace_status"
  fi
  if ssh_capture "command -v rsync >/dev/null 2>&1" >/tmp/aetherville_remote_rsync_check 2>&1; then
    cat /tmp/aetherville_remote_rsync_check
    echo "Remote sync method: rsync"
  else
    cat /tmp/aetherville_remote_rsync_check || true
    echo "Remote sync method: tar-over-ssh fallback (remote rsync unavailable)"
  fi
  echo "Dry-run mode action: $DEPLOY_MODE"
  exit 0
fi

ssh_capture "mkdir -p '$RUNPOD_REMOTE_DIR'"
if ! sync_repository; then
  echo "Repository sync failed."
  exit 12
fi

case "$DEPLOY_MODE" in
  bootstrap)
    ssh_capture "cd '$RUNPOD_REMOTE_DIR' && bash infra/runpod/bootstrap_runpod.sh"
    ;;
  sync-only)
    echo "Deploy sync completed; no remote start command requested."
    ;;
  direct)
    ssh_capture "cd '$RUNPOD_REMOTE_DIR' && export AETHERVILLE_VLLM_MODE='${AETHERVILLE_VLLM_MODE:-mock}' AETHERVILLE_REDIS_MODE='${AETHERVILLE_REDIS_MODE:-memory}' AETHERVILLE_BOOTSTRAP_UV='${AETHERVILLE_BOOTSTRAP_UV:-0}' AETHERVILLE_ORCHESTRATOR_PORT='${AETHERVILLE_ORCHESTRATOR_PORT:-8080}' AETHERVILLE_VISION_PORT='${AETHERVILLE_VISION_PORT:-18001}' AETHERVILLE_VLLM_PORT='${AETHERVILLE_VLLM_PORT:-8000}' AETHERVILLE_RESTART_PROCESSES='1' && bash infra/runpod/start_direct_processes.sh && AETHERVILLE_HEALTH_RETRIES='30' AETHERVILLE_HEALTH_SLEEP='0.5' bash infra/runpod/health_check_direct.sh"
    ;;
esac

echo "Deploy completed in mode '$DEPLOY_MODE'."
