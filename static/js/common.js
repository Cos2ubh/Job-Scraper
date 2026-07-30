// Small shared helpers: HTTP wrapper + toast notifications.

window.api = {
  async request(method, url, body) {
    const opts = { method, headers: { "Accept": "application/json" } };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    let resp;
    try {
      resp = await fetch(url, opts);
    } catch (netErr) {
      toast(`Network error: ${netErr.message}`, "error");
      throw netErr;
    }
    const isJson = (resp.headers.get("content-type") || "").includes("application/json");
    const payload = isJson ? await resp.json().catch(() => ({})) : await resp.text();
    if (!resp.ok) {
      const msg = (payload && payload.message) || `HTTP ${resp.status}`;
      toast(msg, "error");
      throw new Error(msg);
    }
    return payload;
  },
  get(url)         { return this.request("GET", url); },
  post(url, body)  { return this.request("POST", url, body); },
  patch(url, body) { return this.request("PATCH", url, body); },
  put(url, body)   { return this.request("PUT", url, body); },
  del(url)         { return this.request("DELETE", url); },
};

window.toast = function toast(msg, kind = "info") {
  const root = document.getElementById("toast-root");
  if (!root) return;
  const el = document.createElement("div");
  const colors = {
    info:  "bg-slate-800 text-white",
    error: "bg-rose-600  text-white",
    ok:    "bg-emerald-600 text-white",
  }[kind] || "bg-slate-800 text-white";
  el.className = `px-4 py-2 rounded-md shadow-lg text-sm ${colors} animate-pulse`;
  el.textContent = msg;
  root.appendChild(el);
  setTimeout(() => { el.classList.remove("animate-pulse"); }, 400);
  setTimeout(() => { el.remove(); }, 3500);
};

window.setStatus = function setStatus(msg) {
  const el = document.getElementById("global-status");
  if (el) el.textContent = msg || "";
};

window.escapeHtml = function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
};

window.fmtDate = function fmtDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch { return ""; }
};

window.matchBadgeClass = function matchBadgeClass(score) {
  if (score == null) return "bg-slate-200 text-slate-700";
  if (score >= 65) return "match-badge-high";
  if (score >= 35) return "match-badge-mid";
  return "match-badge-low";
};
