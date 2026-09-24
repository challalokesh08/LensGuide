# LensGuide — Expo app (native companion)

React Native (Expo SDK 57) client that talks to the Flask backend over the LAN.
Runs in **Expo Go** on all four demo phones.

## Run it

1. Start the backend in plain HTTP mode (React Native won't trust the self-signed cert):

   ```bash
   cd .. && LENSGUIDE_NO_SSL=1 PORT=8001 python3 run.py
   ```

2. Point the app at your laptop's LAN IP in `src/config.js`:

   ```js
   export const API_BASE = "http://<laptop-ip>:8001";
   ```

3. Start Expo and scan the QR with **Expo Go** (update Expo Go to the latest version):

   ```bash
   cd expo-app && npx expo start
   ```

Both devices must be on the same Wi-Fi as the laptop.

## Features

- **Snap** — live camera, upload from gallery, identify → Confidence Gate
  (recognised / top-3 candidates / honest refusal), grounded facts, Nearby,
  Snap to Book, camera-overlay AR view
- **Translate** — capture or pick a sign/menu, on-image translation to en-IN,
  scored against the `menu_sign_images` eval references
- **Explore** — searchable catalogue, full grounded info for every POI

## Notes

- AR in Expo is **camera-overlay mode** (live feed + floating info card) —
  WebXR isn't available inside Expo Go. Every device shows the same look.
- Offline mode intentionally lives in the web app; the native app talks to the
  backend API.