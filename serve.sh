#!/bin/bash
# Run both LensGuide servers from one command:
#   HTTPS web on 8000 (web + WebXR)   -> logs /tmp/lensguide.log
#   HTTP app on 8004 (Expo app)       -> logs /tmp/lensguide-http.log
set -e
cd "$(dirname "$0")"

IP=${HOST_IP:-$(ipconfig getifaddr en0 2>/dev/null || echo localhost)}

pkill -f "python3 run.py" 2>/dev/null || true
sleep 1

python3 run.py > /tmp/lensguide.log 2>&1 &
LENSGUIDE_NO_SSL=1 PORT=8004 python3 run.py > /tmp/lensguide-http.log 2>&1 &

sleep 2

echo "Web  (HTTPS): https://$IP:8000  <- $(curl -sk -m 3 -o /dev/null -w '%{http_code}' https://localhost:8000/api/health)"
echo "App  (HTTP):  http://$IP:8004   <- $(curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:8004/api/health)"
echo "Stop: pkill -f 'python3 run.py'"