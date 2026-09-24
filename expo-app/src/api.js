import { API_BASE } from "./config";

async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, opts);
  } catch (_) {
    throw new Error(
      "Can't reach the LensGuide server. Check the laptop is running and both devices are on the same Wi-Fi."
    );
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

function postImage(path, uri) {
  const form = new FormData();
  form.append("image", { uri, name: "photo.jpg", type: "image/jpeg" });
  return api(path, { method: "POST", body: form });
}

export const identify = (uri) => postImage("/api/identify", uri);
export const translateImage = (uri) => postImage("/api/translate", uri);
export const pois = () => api("/api/pois");
export const poi = (id) => api("/api/poi/" + id);
export const nearby = (id, mode = "best") => api(`/api/poi/${id}/nearby?mode=${mode}`);
export const book = (id) => api("/api/poi/" + id + "/book");