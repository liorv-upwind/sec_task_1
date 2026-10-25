
#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
POST_INSTALL="${SCRIPT_DIR}/post_install.sh"
LOG_DIR="${APP_DIR}/logs"
LOG_FILE="${LOG_DIR}/setup.log"

if [[ ! -f "${POST_INSTALL}" ]]; then
  echo "ERROR: post_install.sh not found: ${POST_INSTALL}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"
chmod 700 "${LOG_DIR}"
touch "${LOG_FILE}"
chmod 600 "${LOG_FILE}"

echo "Starting project setup..."
echo "Application directory: ${APP_DIR}"
echo "Setup log: ${LOG_FILE}"

if "${POST_INSTALL}" 2>&1 | tee "${LOG_FILE}"; then
  echo "Setup completed successfully."
else
  status=$?
  echo "ERROR: Setup failed with exit code ${status}." >&2
  echo "Review the setup log: ${LOG_FILE}" >&2
  exit "${status}"
fi
