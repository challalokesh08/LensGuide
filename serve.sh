#!/bin/bash
# Run both LensGuide servers from one command:
#   HTTPS web on 8000 (web + WebXR)   -> logs /tmp/lensguide.log
#   HTTP app on 8004 (Expo app)       -> logs /tmp/lensguide-http.log
set -e
cd "$(dirname "$0")"

IP=${HOST_IP:-$(ipconfig getifaddr en0 2>/dev/null || echo localhost)}

pkill -f "run.py" 2>/dev/null || true
sleep 1

# Prefer the project venv (plain python3 may lack flask). Strip stray env
# vars such as LLM_PROVIDER/PORT so .env and the defaults below win.
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

env -u LLM_PROVIDER -u GEMINI_API_KEY -u GEMINI_MODEL PORT=8000 \
  "$PY" run.py > /tmp/lensguide.log 2>&1 &
LENSGUIDE_NO_SSL=1 PORT=8004 \
  "$PY" run.py > /tmp/lensguide-http.log 2>&1 &

# Wait for both servers to answer (up to ~10s) before reporting.
for i in $(seq 1 20); do
  W=$(curl -sk -m 2 -o /dev/null -w '%{http_code}' https://localhost:8000/api/health || true)
  A=$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://localhost:8004/api/health || true)
  [ "$W" = "200" ] && [ "$A" = "200" ] && break
  sleep 0.5
done

echo "Web  (HTTPS): https://$IP:8000  <- $W"
echo "App  (HTTP):  http://$IP:8004   <- $A"
echo "Stop: pkill -f 'run.py'"
