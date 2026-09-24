// LAN address of the laptop running the LensGuide Flask backend
// (plain HTTP — see run.py LENSGUIDE_NO_SSL=1, port 8001 for the app server).
// Refresh with: ipconfig getifaddr en0  (macOS) / ipconfig (Windows)
export const API_BASE = "http://10.10.3.195:8001";