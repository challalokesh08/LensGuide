"use strict";

const $ = (id) => document.getElementById(id);

let stream = null;
let curImage = null; // { file, objectUrl }
let curResult = null; // identify result
let curPoiId = null; // currently loaded poi_id
let offlineMode = false;
let availablePois = null;

/* ---------- tabs ---------- */
document.querySelectorAll(".tab").forEach((t) => {
  t.addEventListener("click", () => switchTab(t.dataset.tab));
});
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  $("view-" + name).classList.add("active");
  if (name === "snap") startCamera();
  if (name === "browse" && !availablePois) loadPoiList();
}
window.switchTab = switchTab;

/* ---------- toast / loading ---------- */
let toastTimer = null;
function toast(msg, ms = 2600) {
  const el = $("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), ms);
}
function showLoading(on) {
  $("loading").hidden = !on;
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.status + " " + path);
  return data;
}

/* ---------- provider badge ---------- */
api("/api/health").then((h) => {
  const b = $("provider-badge");
  b.classList.add(h.provider === "offline" ? "offline" : "live");
  b.textContent = h.provider === "offline" ? "offline" : h.provider.toUpperCase();
}).catch(() => {});

/* ---------- camera ---------- */
function isSecure() {
  return window.isSecureContext || location.hostname === "localhost" || location.hostname === "127.0.0.1";
}
function stopCamera() {
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
}
let camState = "idle"; // idle | starting | ready | denied | insecure | error

function camIsSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

function showCamOverlay(kind, title, sub) {
  camState = kind;
  const off = $("camera-off"), start = $("cam-start");
  if (kind === "ready") { off.hidden = true; start.hidden = true; return; }
  $("cam-off-title").textContent = title;
  $("cam-off-sub").textContent = sub;
  const retry = $("btn-cam-retry");
  retry.hidden = kind === "insecure" || kind === "idle";
  retry.style.display = retry.hidden ? "none" : "";
  off.hidden = false;
  start.hidden = true;
}

function showCamStart() {
  camState = "idle";
  $("camera-off").hidden = true;
  $("cam-start").hidden = false;
}

function camErrorMessage(name) {
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return ["Camera blocked", "Tap the camera icon (🔒) in the address bar → Allow, then Retry. Or use Upload."];
    case "NotFoundError":
    case "OverconstrainedError":
      return ["No camera found", "This device has no rear camera. Use Upload instead."];
    case "NotReadableError":
      return ["Camera in use", "Another app holds the camera. Close it, then Retry."];
    default:
      return ["Camera could not start", "Error " + (name || "unknown") + ". Retry, or use Upload."];
  }
}

async function startCamera(force) {
  if (!camIsSupported()) {
    showCamOverlay("insecure", "Camera not supported", "This browser has no camera support. Use Upload.");
    return;
  }
  if (!isSecure()) {
    showCamOverlay("insecure", "Camera needs HTTPS", "Open the page from the laptop's https://… address, or use Upload. (Camera is blocked on plain http.)");
    return;
  }
  if (stream) { showCamOverlay("ready", "", ""); return; }
  if (camState === "starting" && !force) return;
  camState = "starting";
  if (navigator.permissions && navigator.permissions.query) {
    try {
      const st = await navigator.permissions.query({ name: "camera" });
      if (st.state === "denied") {
        showCamOverlay("denied", "Camera blocked",
          "You previously denied camera access. Allow it in the browser settings (site permissions), then Retry — or use Upload.");
        return;
      }
    } catch (e) { /* camera permission enum unsupported — try getUserMedia anyway */ }
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", aspectRatio: 4 / 3 },
      audio: false,
    });
    $("camera").srcObject = stream;
    showCamOverlay("ready", "", "");
  } catch (e) {
    console.warn(e);
    const [t, s] = camErrorMessage(e.name);
    showCamOverlay("error", t, s);
  }
}

function startCameraFromTap() {
  startCamera(true);
}

function pickUpload() { $("file-input").click(); }
$("file-input").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (f) setImage(f);
});
function setImage(file) {
  stopCamera();
  if (curImage) URL.revokeObjectURL(curImage.objectUrl);
  curImage = { file, objectUrl: URL.createObjectURL(file) };
  const cam = $("camera");
  cam.srcObject = null;
  cam.src = curImage.objectUrl;
  $("snap-overlay").hidden = true;
  $("btn-identify").disabled = false;
}
window.dismissSnapOverlay = dismissSnapOverlay;
function snap() {
  if (!stream) {
    if (curImage) { dismissSnapOverlay(); return toast("Photo captured — tap Identify"); }
    showCamStart();
    return toast("Camera not ready. Tap Start camera (or Upload).", 3200);
  }
  const v = $("camera");
  if (!v.videoWidth) { showCamStart(); return toast("Camera still starting — wait a moment, then retry.", 3200); }
  const canvas = document.createElement("canvas");
  canvas.width = v.videoWidth || 1280;
  canvas.height = v.videoHeight || 960;
  canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
  canvas.toBlob((blob) => {
    if (curImage) URL.revokeObjectURL(curImage.objectUrl);
    curImage = { file: new File([blob], "snap.jpg", { type: "image/jpeg" }), objectUrl: URL.createObjectURL(blob) };
    $("snap-img").src = curImage.objectUrl;
    $("snap-overlay").hidden = false;
    $("btn-identify").disabled = false;
  }, "image/jpeg", 0.92);
}

function dismissSnapOverlay() {
  $("snap-overlay").hidden = true;
}

/* ---------- identify ---------- */
async function identify() {
  if (!curImage) return toast("Snap or upload a photo first");
  showLoading(true);
  try {
    const fd = new FormData();
    fd.append("image", curImage.file);
    const r = await api("/api/identify", { method: "POST", body: fd });
    curResult = r;
    renderIdentify(r);
  } catch (e) {
    $("result-card").innerHTML = errorBox(e);
  } finally {
    showLoading(false);
  }
}
$("btn-identify").addEventListener("click", identify);

function renderIdentify(r) {
  const el = $("result-card");
  el.hidden = false;

  // Confidence Gate: below threshold we never name a subject.
  if (r.status === "candidates") return renderCandidates(el, r);
  if (r.status === "not_recognised") return renderRefusal(el, r);

  let html = `<div class="card"><div class="card-head">
    <div><h2>${esc(r.name || "Hmm, not sure")}</h2>
    <div class="sub">${esc(r.description || "")}</div></div>
    <span class="kind-tag conf ${levelClass(r.confidence)}">${esc(r.confidence)} · ${Math.round(r.confidence_score * 100)}%</span></div>`;

  if (r.ocr_text) {
    html += `<div class="card-body"><div class="fact-box"><p class="fact-text"><b>OCR:</b> ${esc(r.ocr_text)}</p>
      <button class="btn btn-accent" style="width:100%" onclick="openTranslateFromText(${JSON.stringify(r.ocr_text)})">Translate</button></div></div>`;
    curText = r.ocr_text;
  }

  if (r.matched) {
    curPoiId = r.matched.poi_id;
    html += renderMatchActions(r.matched);
    loadPoiInfo(curPoiId).then((infoHtml) => {
      $("poi-info-slot").innerHTML = infoHtml;
    });
  } else if (r.kind && r.kind !== "unknown") {
    html += `<div class="card-body"><p class="hint">Recognised, but this subject is not in the catalogue — pick from the explore tab, or try again.</p></div>`;
  }
  html += `<div id="poi-info-slot"></div></div>`;
  el.innerHTML = html;
}

function renderCandidates(el, r) {
  el.innerHTML = `<div class="card"><div class="card-head">
    <div><h2>Which one did you mean?</h2>
    <div class="sub">That photo didn't clear the confidence bar (${Math.round(r.confidence_score * 100)}%) — tap the match below.</div></div>
    <span class="kind-tag conf medium">choose one</span></div>
    <div class="card-body">
      ${r.candidates.map((c) => `<button class="btn btn-ghost candidate" onclick="chooseCandidate('${c.poi_id}')">
        <span>${esc(c.name)}</span><span class="conf medium">${Math.round(c.score * 100)}%</span></button>`).join("")}
    </div></div>`;
}

function renderRefusal(el) {
  el.innerHTML = `<div class="card"><div class="card-head">
    <div><h2>Not recognised</h2>
    <div class="sub">No match was confident enough — I won't guess.</div></div>
    <span class="kind-tag conf medium">no guess</span></div>
    <div class="card-body">
      <p class="hint">Try a clearer straight-on angle, or search the catalogue manually.</p>
      <button class="btn btn-accent" style="width:100%" onclick="switchTab('browse')">Browse catalogue</button>
    </div></div>`;
}

async function chooseCandidate(poiId) {
  curPoiId = poiId;
  const el = $("result-card");
  el.hidden = false;
  el.innerHTML = `<div class="card"><div class="sub">Grounding on your choice…</div><div id="poi-info-slot"></div></div>`;
  showLoading(true);
  try {
    const infoHtml = await loadPoiInfo(poiId);
    el.innerHTML = `<div class="card">${renderMatchActions({ poi_id: poiId, name: "" })}<div id="poi-info-slot">${infoHtml}</div></div>`;
    curResult = { matched: { poi_id: poiId, name: el.querySelector("h2")?.textContent || "" } };
    toast("Grounded on your choice");
  } catch (e) {
    el.innerHTML = errorBox(e);
  } finally {
    showLoading(false);
  }
}

let curText = "";

function renderMatchActions(m) {
  return `<div class="card-actions">
    <button class="btn btn-ghost" onclick="fetchNearest()">Nearby</button>
    <button class="btn btn-ghost" onclick="fetchBook()">Snap to Book</button>
    <button class="btn btn-primary" onclick="startAR()">◉ AR View</button>
  </div>`;
}

async function loadPoiInfo(poiId) {
  try {
    const info = await api("/api/poi/" + poiId);
    return renderPoiCard(info.poi) + renderFacts(info.facts) + renderKnowledge(info.knowledge);
  } catch (e) {
    return errorBox(e);
  }
}

function renderPoiCard(p) {
  return `<div class="card-body">
    <div class="sub">${esc(p.poi_category)} · ${esc(p.city_name)}, ${esc(p.country_name)}</div>
    <p style="margin:6px 0 10px;font-size:14px;line-height:1.5">${esc(p.description)}</p>
    <div class="fact-box"><div class="sub">Entry</div><b>${esc(p.entry_cost_display)}</b></div>
  </div>`;
}
function renderFacts(facts) {
  return `<div class="card-body">
    <div class="kb-title">Grounded facts</div>
    ${facts.map((f) => `<div class="fact-box">
      <p class="fact-text">${esc(f.fact_text)}</p>
      <span class="conf ${levelClass(f.confidence)}">${esc(f.confidence)}</span>
      <span class="sub"> · ${esc(f.fact_type)}</span>
    </div>`).join("")}</div>`;
}
function renderKnowledge(kb) {
  return `<div class="card-body">` + kb.map((k) =>
    `<div class="kb-title">${esc(k.title)}</div><p class="kb-body">${esc(k.body)}</p>`
  ).join("") + `</div>`;
}
function levelClass(c) { return ["high", "medium", "low"].includes(c) ? c : "low"; }
function esc(s) { return (s ?? "").toString().replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function errorBox(e) { return `<div class="card"><div class="card-body error-box">⚠ ${esc(e.message || e)}</div></div>`; }

/* ---------- nearby ---------- */
async function fetchNearest() {
  if (!curPoiId) return toast("Recognition didn't ground a POI yet.");
  $("nearby-sheet").hidden = false;
  $("nearby-context").textContent = "loading…";
  loadNearby("best");
}
function closeSheet(id) { $(id).hidden = true; }
window.closeSheet = closeSheet;

async function loadNearby(mode) {
  if (!curPoiId) return;
  document.querySelectorAll(".mtab").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  $("nearby-context").textContent = "people also went to";
  $("nearby-list").innerHTML = `<div class="hint">Loading…</div>`;
  try {
    const d = await api(`/api/poi/${curPoiId}/nearby?mode=${mode}&limit=6`);
    const items = d.nearby.map((n, i) => `
      <div class="nb-item">
        <div class="nb-rank">${i + 1}</div>
        <div style="flex:1">
          <b>${esc(n.name)}</b>
          <div class="nb-meta">${n.minutes} min · ${n.distance_km} km · ${n.cost_display} · bearing ${n.bearing_deg}°<br>
          ${n.carbon_kg} kg CO₂ · <span class="conf ${levelClass((n.popularity_score || 0) > 70 ? "high" : (n.popularity_score || 0) > 40 ? "medium" : "low")}">pop ${n.popularity_score}</span></div>
        </div>
      </div>`).join("");
    $("nearby-list").innerHTML = items || `<div class="hint">Nothing on foot nearby.</div>`;
  } catch (e) {
    $("nearby-list").innerHTML = errorBox(e);
  }
}
window.loadNearby = loadNearby;

/* ---------- book ---------- */
async function fetchBook() {
  if (!curPoiId) return toast("Nothing grounded yet.");
  showLoading(true);
  try {
    const b = await api(`/api/poi/${curPoiId}/book`);
    $("book-title").textContent = b.name;
    const hrs = b.opens_at && b.closes_at ? `${b.opens_at} – ${b.closes_at}` : "Open all day";
    $("book-body").innerHTML = `
      <div class="book-row"><span class="k">Entry</span><b>${esc(b.entry_cost_display)}</b></div>
      <div class="book-row"><span class="k">Currency</span><b>${esc(b.currency)} (${esc(b.currency_display.name)})</b></div>
      <div class="book-row"><span class="k">Hours</span><b>${esc(hrs)}</b></div>
      <div class="book-row"><span class="k">Closed days</span><b>${b.closed_days.length ? b.closed_days.join(", ") : "None"}</b></div>
      <div class="book-row"><span class="k">Typical visit</span><b>${b.typical_duration_minutes} min</b></div>
      <div class="book-row"><span class="k">Accessibility</span><b>${esc(b.accessibility)}</b></div>
      <div class="book-row"><span class="k">Best season</span><b>${esc(b.best_season || "—")}</b></div>
      <div class="book-row"><span class="k">Carbon</span><b>${b.carbon_kg} kg</b></div>
      <div class="book-row"><span class="k">XR preview</span><b>${b.has_xr_scene ? "Available" : "No"}</b></div>
      <p class="hint" style="margin-top:12px">${esc(b.description)}</p>`;
    $("book-modal").hidden = false;
  } catch (e) {
    toast("Could not load booking info");
  } finally {
    showLoading(false);
  }
}
window.fetchBook = fetchBook;

/* ---------- translate ---------- */
$("tr-file").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  $("tr-img-name").hidden = false;
  $("tr-img-name").textContent = f.name;
  window.__trFile = f;
});

function openTranslateFromText(text) {
  switchTab("translate");
  $("tr-text").value = decodeText(text);
  translate();
}
window.openTranslateFromText = openTranslateFromText;
function decodeText(t) {
  try { return JSON.parse(t); } catch (_) { return t; }
}

async function translate() {
  const text = $("tr-text").value.trim();
  const img = window.__trFile;
  if (!text && !img) return toast("Add sign text or pick an image");
  showLoading(true);
  try {
    const fd = new FormData();
    if (text) fd.append("text", text);
    if (img) fd.append("image", img);
    const r = await api("/api/translate", { method: "POST", body: fd });
    const el = $("tr-result");
    el.hidden = false;
    let html = `<div class="card"><div class="card-body">
      <p class="fact-text"><b>Original:</b> ${esc(r.ocr_text || text)}</p>
      <p class="fact-text" style="font-size:16px"><b>${esc(r.translation)}</b></p>
      <span class="conf ${levelClass(r.confidence)}">${esc(r.confidence)}</span>
      <span class="sub"> · ${esc(r.source_language)} → ${esc(r.target_language)}</span>`;
    if (r.reference) {
      html += `<div class="fact-box" style="margin-top:10px">
        <p class="fact-text"><b>Reference:</b> ${esc(r.reference.reference_translation)}</p>
        <span class="conf ${r.matches_reference ? "high" : "medium"}">${r.matches_reference ? "matches" : "differs"}</span>
        <span class="sub"> · <span class="kind-tag">${esc(r.reference.kind)}</span></span>`;
      if (r.reference.is_safety_critical) html += `<div class="chip">⚠ safety-critical</div>`;
      html += `</div>`;
    }
    html += `</div></div>`;
    el.innerHTML = html;
  } catch (e) {
    $("tr-result").innerHTML = errorBox(e);
  } finally {
    showLoading(false);
  }
}
window.translate = translate;

/* ---------- AR view (WebXR when available, camera overlay everywhere) ---------- */
let xrSession = null;
let camStream = null;

window.startAR = startAR;
async function startAR() {
  if (!curPoiId) return toast("Recognise a POI first, then view it in AR.");
  stopCamera();              // release the snap camera so AR gets the sole feed
  $("snap-overlay").hidden = true;
  showLoading(true);
  let info;
  try {
    info = await api("/api/poi/" + curPoiId);
  } catch (e) {
    showLoading(false);
    return toast("Could not load POI details");
  }
  $("ar-name").textContent = info.poi.name;
  $("ar-fact").textContent =
    info.facts && info.facts[0] ? info.facts[0].fact_text : info.poi.description;

  // 1) True WebXR immersive-ar where the device supports it.
  let xrOK = false;
  if (navigator.xr) {
    try { xrOK = await navigator.xr.isSessionSupported("immersive-ar"); }
    catch (_) { xrOK = false; }
  }
  if (xrOK) {
    try {
      xrSession = await navigator.xr.requestSession("immersive-ar", {
        requiredFeatures: ["dom-overlay", "local"],
        optionalFeatures: ["hit-test"],
        domOverlay: { root: $("ar-overlay") },
      });
      $("ar-cam").hidden = true;          // WebXR renders its own camera
      $("ar-overlay").hidden = false;
      $("ar-mode").textContent = "WebXR AR";
      $("ar-mode").classList.add("conf", "high");
      xrSession.addEventListener("end", exitAR);
      const tick = () => { if (xrSession) xrSession.requestAnimationFrame(tick); };
      xrSession.requestAnimationFrame(tick);
      showLoading(false);
      return;
    } catch (e) {
      exitAR();
    }
  }
  showLoading(false);
  // 2) Universal camera-overlay AR — works on every device over HTTPS.
  await startCameraOverlayAR();
}

async function startCameraOverlayAR() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !isSecure()) {
    return toast("AR overlay needs camera + HTTPS. Use the grounded info below instead.");
  }
  try {
    camStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    $("ar-cam").srcObject = camStream;
    $("ar-cam").hidden = false;
    $("ar-overlay").hidden = false;
    $("ar-mode").textContent = "Overlay AR";
    $("ar-mode").classList.remove("conf", "high");
  } catch (e) {
    toast("AR camera unavailable (" + (e.name || e.message) + ") — tap × Exit AR and give camera permission.", 4000);
    console.warn(e);
  }
}

function exitAR() {
  if (xrSession) { try { xrSession.end(); } catch (_) {} xrSession = null; }
  if (camStream) { camStream.getTracks().forEach((t) => t.stop()); camStream = null; }
  $("ar-cam").srcObject = null;
  $("ar-cam").hidden = true;
  $("ar-overlay").hidden = true;
}
window.exitAR = exitAR;

/* ---------- offline / browse ---------- */
function toggleOffline() {
  offlineMode = $("offline-toggle").checked;
  document.body.classList.toggle("offline", offlineMode);
  if (offlineMode) {
    switchTab("browse");
    loadPoiList();
    toast("Offline demo mode — everything is served from the local database");
  } else {
    switchTab("snap");
    startCamera();
  }
}
window.toggleOffline = toggleOffline;

async function loadPoiList() {
  try {
    availablePois = await api("/api/pois");
    const sel = $("poi-select");
    sel.innerHTML = `<option value="">— choose a place —</option>` + availablePois
      .map((p) => `<option value="${p.poi_id}">${esc(p.name)} · ${esc(p.city)}</option>`)
      .join("");
  } catch (e) {
    $("browse-card").innerHTML = errorBox(e);
  }
}
window.loadPoiList = loadPoiList;

async function useMyLocation() {
  if (!("geolocation" in navigator)) { toast("Geolocation not supported"); return; }
  toast("Getting your location…");
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude: lat, longitude: lng } = pos.coords;
      try {
        const d = await api(`/api/nearby?lat=${lat}&lng=${lng}&limit=10`);
        const list = d.nearby.map((p, i) =>
          `<button class="btn btn-ghost candidate" onclick="loadPoiFromSelect(); $('poi-select').value='${p.poi_id}'; loadPoiFromSelect();">
             ${i + 1}. ${esc(p.name)} · <span class="sub">${p.distance_km} km</span>
           </button>`
        ).join("");
        $("browse-card").hidden = false;
        $("browse-card").innerHTML = `<div class="card"><div class="card-body"><h3>Nearby (${d.nearby.length})</h3>${list || "<span class='hint'>No POIs nearby.</span>"}</div></div>`;
        toast("Location found — showing nearby places");
      } catch (e) {
        toast("Failed to load nearby places");
      }
    },
    () => toast("Location permission denied"),
    { enableHighAccuracy: true, timeout: 10000 }
  );
}
window.useMyLocation = useMyLocation;

async function loadPoiFromSelect() {
  const id = $("poi-select").value;
  const box = $("browse-card");
  if (!id) { box.hidden = true; return; }
  box.hidden = false;
  curPoiId = id;
  showLoading(true);
  try {
    await loadPoiInfo(id).then((html) => {
      box.innerHTML = `<div class="card">${renderMatchActions({ poi_id: id, name: "" })}<div id="poi-info-slot">${html}</div></div>`;
      curResult = { matched: { poi_id: id, name: box.querySelector("h2")?.textContent || "" } };
    });
  } catch (e) {
    box.innerHTML = errorBox(e);
  } finally {
    showLoading(false);
  }
}
window.loadPoiFromSelect = loadPoiFromSelect;

/* ---------- shell ---------- */
window.addEventListener("pagehide", stopCamera);
showCamStart();