#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/write_macbook_demo_env.sh --mode tunnel [--dry-run]
  AETHERVILLE_DEMO_ORCHESTRATOR_URL=https://... scripts/write_macbook_demo_env.sh --mode public [--dry-run]

Writes client/.env.local for a MacBook browser demo without printing endpoint values.
The generated file is ignored by git and must not be committed.
USAGE
}

mode=""
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$mode" in
  tunnel)
    orchestrator_url="http://127.0.0.1:18080"
    ;;
  public)
    orchestrator_url="${AETHERVILLE_DEMO_ORCHESTRATOR_URL:-}"
    if [[ -z "$orchestrator_url" ]]; then
      echo "AETHERVILLE_DEMO_ORCHESTRATOR_URL is required for --mode public" >&2
      exit 2
    fi
    if [[ ! "$orchestrator_url" =~ ^https?:// ]]; then
      echo "AETHERVILLE_DEMO_ORCHESTRATOR_URL must start with http:// or https://" >&2
      exit 2
    fi
    ;;
  "")
    echo "--mode is required" >&2
    usage >&2
    exit 2
    ;;
  *)
    echo "Unsupported mode: $mode" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$dry_run" -eq 1 ]]; then
  echo "Would write client/.env.local for '$mode' mode. Endpoint value intentionally not printed."
  exit 0
fi

mkdir -p client
umask 077
tmp_file="$(mktemp client/.env.local.XXXXXX)"
trap 'rm -f "$tmp_file"' EXIT

cat > "$tmp_file" <<EOF_ENV
NEXT_PUBLIC_ORCHESTRATOR_URL=$orchestrator_url
NEXT_PUBLIC_SOCKET_URL=$orchestrator_url
NEXT_PUBLIC_SOCKET_TRANSPORTS=polling
EOF_ENV

mv "$tmp_file" client/.env.local
trap - EXIT

echo "Wrote client/.env.local for '$mode' mode. Endpoint value intentionally not printed."
