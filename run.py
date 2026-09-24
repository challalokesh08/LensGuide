import os
from pathlib import Path

for line in Path(__file__).parent.joinpath(".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip())

from lensguide.app import app


def ssl_context():
    """HTTPS when a cert has been generated (scripts/gen_cert.sh) or ad-hoc requested.
    Set LENSGUIDE_NO_SSL=1 to serve plain HTTP — required by the Expo app
    (React Native won't trust a self-signed cert)."""
    if os.environ.get("LENSGUIDE_NO_SSL") == "1":
        return None
    if os.path.exists("certs/cert.pem") and os.path.exists("certs/key.pem"):
        return ("certs/cert.pem", "certs/key.pem")
    if os.environ.get("SSL_ADHOC"):
        return "adhoc"
    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    ssl = ssl_context()
    print(f"LensGuide running at http{'s' if ssl else ''}://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True, ssl_context=ssl)