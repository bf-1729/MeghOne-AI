#!/usr/bin/env bash
# Start the web app in the background for Playwright E2E tests.
#
# Detection order:
#   1. APP_MODULE repository variable (e.g. "app.main:app")  -> uvicorn
#   2. manage.py present                                      -> Django runserver
#   3. a file containing "FastAPI("                           -> uvicorn <module>:app
# If nothing is found, no app is started and E2E tests skip themselves.
#
# On success writes the URL to .ci_base_url, the PID to .ci_app_pid, logs to app.log.
set -euo pipefail

PORT="${APP_PORT:-8000}"
URL="http://127.0.0.1:${PORT}"
PY="${PYTHON:-$(command -v python3 || command -v python)}"   # PYTHON overrides (e.g. local venv)

if [ -n "${APP_MODULE:-}" ]; then
  echo "Starting FastAPI/ASGI app from APP_MODULE=${APP_MODULE}"
  "$PY" -m pip install --quiet uvicorn
  nohup "$PY" -m uvicorn "$APP_MODULE" --host 127.0.0.1 --port "$PORT" > app.log 2>&1 &

elif [ -f manage.py ]; then
  echo "Detected Django (manage.py)"
  "$PY" manage.py migrate --noinput
  nohup "$PY" manage.py runserver "127.0.0.1:${PORT}" --noreload > app.log 2>&1 &

else
  FASTAPI_FILE="$(grep -rl --include='*.py' -E 'FastAPI\(' . \
      --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=tests 2>/dev/null | head -n1 || true)"
  if [ -n "$FASTAPI_FILE" ]; then
    MODULE="$(echo "${FASTAPI_FILE#./}" | sed -e 's/\.py$//' -e 's#/#.#g')"
    echo "Detected FastAPI in ${FASTAPI_FILE} -> ${MODULE}:app"
    "$PY" -m pip install --quiet uvicorn
    nohup "$PY" -m uvicorn "${MODULE}:app" --host 127.0.0.1 --port "$PORT" > app.log 2>&1 &
  else
    echo "No Django/FastAPI app found yet - E2E tests will be skipped."
    exit 0
  fi
fi

echo $! > .ci_app_pid
echo "Waiting for ${URL} ..."
for i in $(seq 1 60); do
  if "$PY" -c "import urllib.request,sys; urllib.request.urlopen('${URL}', timeout=2)" 2>/dev/null \
     || "$PY" -c "import urllib.request,urllib.error,sys
try: urllib.request.urlopen('${URL}', timeout=2)
except urllib.error.HTTPError: sys.exit(0)
sys.exit(1)" 2>/dev/null; then
    echo "App is up after ${i}s"
    echo "$URL" > .ci_base_url
    exit 0
  fi
  sleep 1
done

echo "App did not start within 60s. Last log lines:"
tail -n 50 app.log || true
exit 1
