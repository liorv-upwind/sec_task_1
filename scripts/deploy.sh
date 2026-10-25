#!/usr/bin/env bash
#
# Deploy the built wheel to a remote VM over SSH and install it into a venv.
#
# What it does:
#   1. Builds the wheel locally (unless one is passed in / found in dist/).
#   2. Copies the wheel to the remote host via scp.
#   3. Creates/refreshes a venv in the remote app dir and installs the wheel.
#   4. Optionally starts the health service (loopback) in the background.
#
# It installs the package and (optionally) starts the `ec2-health` service only.
# It never runs the read/extract/publish chain -- that stays an explicit,
# per-run decision on the host.
#
# Usage:
#   scripts/deploy.sh user@host [options]
#
# Options (also settable via env):
#   -i, --identity PATH    SSH private key                (SSH_KEY)
#   -d, --remote-dir PATH  Remote app dir (default: ~/sec-task-1)  (REMOTE_DIR)
#   -w, --wheel PATH       Wheel to deploy (default: newest in dist/)  (WHEEL)
#   -p, --port PORT        APP_PORT for the started service (default: 5000)  (APP_PORT)
#       --start            Start ec2-health on loopback after install
#       --no-build         Do not build; require an existing wheel
#   -h, --help             Show this help
#
# Examples:
#   scripts/deploy.sh ec2-user@10.0.0.5 -i ~/.ssh/key.pem
#   scripts/deploy.sh ec2-user@host --start --port 5000

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET=""
SSH_KEY="${SSH_KEY:-}"
REMOTE_DIR="${REMOTE_DIR:-sec-task-1}"
WHEEL="${WHEEL:-}"
APP_PORT="${APP_PORT:-5000}"
DO_BUILD=1
DO_START=0

usage() { sed -n '2,/^set -Eeuo/{/^set -Eeuo/d;p;}' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//; s/^#$//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--identity)   SSH_KEY="$2"; shift 2 ;;
    -d|--remote-dir) REMOTE_DIR="$2"; shift 2 ;;
    -w|--wheel)      WHEEL="$2"; shift 2 ;;
    -p|--port)       APP_PORT="$2"; shift 2 ;;
    --start)         DO_START=1; shift ;;
    --no-build)      DO_BUILD=0; shift ;;
    -h|--help)       usage; exit 0 ;;
    -*)              echo "ERROR: unknown option: $1" >&2; exit 2 ;;
    *)               if [[ -z "${TARGET}" ]]; then TARGET="$1"; shift;
                     else echo "ERROR: unexpected argument: $1" >&2; exit 2; fi ;;
  esac
done

if [[ -z "${TARGET}" ]]; then
  echo "ERROR: missing target (user@host). See --help." >&2
  exit 2
fi

SSH_OPTS=()
[[ -n "${SSH_KEY}" ]] && SSH_OPTS+=(-i "${SSH_KEY}")

# 1. Build (unless disabled) and locate the wheel.
if [[ -z "${WHEEL}" && ${DO_BUILD} -eq 1 ]]; then
  echo "[1/4] Building wheel..."
  ( cd "${APP_DIR}" && python3 -m build --wheel >/dev/null )
fi

if [[ -z "${WHEEL}" ]]; then
  WHEEL="$(ls -t "${APP_DIR}"/dist/*.whl 2>/dev/null | head -n1 || true)"
fi

if [[ -z "${WHEEL}" || ! -f "${WHEEL}" ]]; then
  echo "ERROR: no wheel found. Build one (python -m build) or pass --wheel PATH." >&2
  exit 1
fi
WHEEL_BASE="$(basename "${WHEEL}")"
echo "[1/4] Using wheel: ${WHEEL_BASE}"

# 2. Copy the wheel to the remote host.
echo "[2/4] Copying wheel to ${TARGET}:${REMOTE_DIR}/ ..."
ssh "${SSH_OPTS[@]}" "${TARGET}" "mkdir -p '${REMOTE_DIR}'"
scp "${SSH_OPTS[@]}" "${WHEEL}" "${TARGET}:${REMOTE_DIR}/${WHEEL_BASE}"

# 3. Create/refresh the venv and install the wheel (remote).
echo "[3/4] Installing on remote host..."
ssh "${SSH_OPTS[@]}" "${TARGET}" bash -s -- "${REMOTE_DIR}" "${WHEEL_BASE}" <<'REMOTE'
set -Eeuo pipefail
REMOTE_DIR="$1"
WHEEL_BASE="$2"
cd "${REMOTE_DIR}"
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required on host." >&2; exit 1; }
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
./.venv/bin/python -m pip install --upgrade pip >/dev/null
./.venv/bin/python -m pip install --upgrade "./${WHEEL_BASE}"
echo "Installed commands:"
ls .venv/bin | grep -E '^ec2-' || true
REMOTE

# 4. Optionally start the health service on loopback.
if [[ ${DO_START} -eq 1 ]]; then
  echo "[4/4] Starting ec2-health (loopback, port ${APP_PORT})..."
  ssh "${SSH_OPTS[@]}" "${TARGET}" bash -s -- "${REMOTE_DIR}" "${APP_PORT}" <<'REMOTE'
set -Eeuo pipefail
REMOTE_DIR="$1"
APP_PORT="$2"
cd "${REMOTE_DIR}"
mkdir -p logs
# Bind to loopback only; override APP_HOST on the host if a proxy fronts it.
APP_HOST=127.0.0.1 APP_PORT="${APP_PORT}" nohup ./.venv/bin/ec2-health >>logs/service.log 2>&1 &
sleep 1
echo "ec2-health started (pid $!), logging to ${REMOTE_DIR}/logs/service.log"
REMOTE
else
  echo "[4/4] Skipping service start (pass --start to launch ec2-health)."
fi

echo "Deploy complete."
