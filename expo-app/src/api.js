import { API_BASE } from "./config";

async function api(path, opts = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...opts, signal: controller.signal });
  } catch (e) {
    const detail = e && e.message ? (e.name === "AbortError" ? "timed out (12s)" : e.message) : "unknown";
    throw new Error(`Can't reach server at ${API_BASE} — ${detail}. Check the laptop is on, on the same Wi-Fi, and that ${API_BASE}/api/health opens on this phone's browser.`);
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    let msg = `Server error (${res.status})`;
    try {
      const j = await res.json();
      if (j.error) msg = j.error;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

export async function ping() {
  try {
    const h = await api("/api/health", {}, 5000);
    return h.ok ? null : "unhealthy";
  } catch (e) {
    return e.message;
  }
}

async function postImage(path, uri) {
  // RN 0.86 no longer accepts { uri, name, type } parts in FormData —
  // read the file into a Blob first.
  const data = await fetch(uri);
  const blob = await data.blob();
  const form = new FormData();
  form.append("image", blob, "photo.jpg");
  return api(path, { method: "POST", body: form });
}

export const identify = (uri) => postImage("/api/identify", uri);
export const translateImage = (uri) => postImage("/api/translate", uri);
export const pois = () => api("/api/pois");
export const poi = (id) => api("/api/poi/" + id);
export const nearby = (id, mode = "best") => api(`/api/poi/${id}/nearby?mode=${mode}`);
export const book = (id) => api("/api/poi/" + id + "/book");