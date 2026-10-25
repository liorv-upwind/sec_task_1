
#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="${APP_DIR}/.venv"

echo "[1/5] Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: python3 is required." >&2
  exit 1
}

if [[ ! -f "${APP_DIR}/requirements.txt" ]]; then
  echo "ERROR: requirements.txt not found in ${APP_DIR}" >&2
  exit 1
fi

echo "[2/5] Checking /etc/passwd readability..."

if [[ -r /etc/passwd ]]; then
  echo "/etc/passwd exists and is readable."
  echo "Number of lines: $(wc -l < /etc/passwd)"
else
  echo "ERROR: /etc/passwd is not readable." >&2
  exit 1
fi

echo "[3/5] Creating Python virtual environment..."

python3 -m venv "${VENV_DIR}"

echo "[4/5] Installing dependencies..."

"${VENV_DIR}/bin/python" -m pip install \
  -r "${APP_DIR}/requirements.txt"

echo "[5/5] Running tests and validating the application..."

if [[ -d "${APP_DIR}/tests" ]]; then
  (
    cd "${APP_DIR}"
    "${VENV_DIR}/bin/python" -m unittest discover -s tests -t .
  )
else
  echo "WARNING: No tests directory found; skipping tests."
fi

(
  cd "${APP_DIR}"
  "${VENV_DIR}/bin/python" -c "import app"
)

echo "All post-install checks completed successfully."
echo "To start the application:"
echo "  cd '${APP_DIR}'"
echo "  '${VENV_DIR}/bin/python' app.py"
