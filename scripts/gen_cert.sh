#!/bin/bash
# Generate a self-signed cert for LAN HTTPS so getUserMedia works on the phones.
# Run once on the demo laptop, then serve with  python run.py
# Devices must accept the cert once in their browser (type "thisisunsafe" on the
# warning page) — do this before the demo, never during.

set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p certs

LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -subj "/CN=${LAN_IP}" \
  -addext "subjectAltName=IP:${LAN_IP},DNS:localhost"

echo ""
echo "Certificate created in certs/"
echo "Now just:  python3 run.py   (it picks up certs/ automatically)"
echo "Then open on the phones:  https://${LAN_IP}:8000"
echo "Accept the cert warning once on each phone (type: thisisunsafe)."