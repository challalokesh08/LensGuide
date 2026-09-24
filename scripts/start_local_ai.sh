#!/bin/bash
# Start the local LM Studio vision model used by LensGuide.
set -e

LMS="/Applications/LM Studio.app/Contents/Resources/app/.webpack/lms"
MODEL="qwen/qwen3.5-4b"
IDENTIFIER="qwen/qwen3.5-4b:fast"

if [ ! -x "$LMS" ]; then
  echo "LM Studio CLI not found at $LMS" >&2
  exit 1
fi

open -a "LM Studio"
for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:1234/v1/models >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

"$LMS" server start --port 1234 >/tmp/lensguide-lmstudio.log 2>&1 || true
"$LMS" load "$MODEL" --context-length=2048 --parallel=1 --gpu=max --identifier "$IDENTIFIER" -y || true

echo "LensGuide local AI is running at http://127.0.0.1:1234/v1"
