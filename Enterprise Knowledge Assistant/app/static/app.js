/* =========================================================
   Enterprise Knowledge Assistant — front-end logic
   Single-page chat UI. Consumes the FastAPI endpoints:
     GET    /api/documents      list library
     POST   /api/documents      upload + index
     DELETE /api/documents/{id} remove a document
     POST   /api/ask/stream     SSE answer stream
     POST   /api/search/compare retrieval ablation (no LLM)
     GET    /api/stats          index health
   ========================================================= */

"use strict";

/* ---------------------------------------------------------
   Icons (feather-style, 24px stroke icons)
   --------------------------------------------------------- */

const ICONS = {
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 14.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4Z"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="6" y="6" width="12" height="12" rx="2.5"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6M14 11v6"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  cols: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="4.6" height="16" rx="1.4"/><rect x="9.7" y="4" width="4.6" height="16" rx="1.4"/><rect x="16.4" y="4" width="4.6" height="16" rx="1.4"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  page: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M12 12v5"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>',
  thumbUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.9 14 10h5.5a1.5 1.5 0 0 1 1.5 1.7l-1.3 7.5a2 2 0 0 1-2 1.7H7a1 1 0 0 1-1-1V11a1 1 0 0 1 1-1h3.2l1.6-4.6A2 2 0 0 1 13.8 4h.4a1.3 1.3 0 0 1 .8 1.9Z"/></svg>',
  thumbDown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.1 10 14H4.5A1.5 1.5 0 0 1 3 12.3l1.3-7.5A2 2 0 0 1 6.3 3.1H17a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-3.2l-1.6 4.6A2 2 0 0 1 10.2 20h-.4a1.3 1.3 0 0 1-.8-1.9Z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
};

/* ---------------------------------------------------------
   Tiny helpers
   --------------------------------------------------------- */

const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

function el(tag, cls, html) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
}

function iconEl(name, cls) {
  const s = el("span", cls || "");
  s.innerHTML = ICONS[name] || "";
  return s;
}

function hydrateIcons(root) {
  $$("[data-icon]", root).forEach((n) => {
    const name = n.getAttribute("data-icon");
    if (ICONS[name]) n.innerHTML = ICONS[name];
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function fmtNum(n) {
  return Number(n || 0).toLocaleString("en-US");
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtScore(v) {
  if (v == null || !Number.isFinite(Number(v))) return "—";
  const n = Number(v);
  return n.toFixed(4).replace(/\.?0+$/, "");
}

/* ---------------------------------------------------------
   DOM references
   --------------------------------------------------------- */

const libPanel = $("#libPanel");
const evPanel = $("#evPanel");
const backdrop = $("#backdrop");
const lib = $("#lib");
const libCount = $("#libCount");
const drop = $("#drop");
const fileInput = $("#fileInput");
const deptSel = $("#dept");
const sensSel = $("#sensitivity");
const statDocs = $("#statDocs");
const statChunks = $("#statChunks");
const statVectors = $("#statVectors");

const thread = $("#thread");
const emptyState = $("#emptyState");
const input = $("#input");
const sendBtn = $("#sendBtn");
const stopBtn = $("#stopBtn");
const composerHint = $("#composerHint");

const viewAsk = $("#viewAsk");
const viewCompare = $("#viewCompare");
const cmpIntro = $("#cmpIntro");
const cmpQbar = $("#cmpQbar");
const cmpGrid = $("#cmpGrid");
const cmpQText = $("#cmpQText");

const railBody = $("#evBody");
const railSub = $("#evSub");
const evCount = $("#evCount");

const chats = $("#chats");
const newChatBtn = $("#newChatBtn");
const sideTabChats = $("#sideTabChats");
const sideTabLib = $("#sideTabLib");
const sideViewChats = $("#sideViewChats");
const sideViewLib = $("#sideViewLib");
const tabChatCount = $("#tabChatCount");
const tabLibCount = $("#tabLibCount");

/* ---------------------------------------------------------
   State
   --------------------------------------------------------- */

let view = "ask";            // "ask" | "compare"
let streaming = false;
let abortCtrl = null;
let history = [];            // chat history sent with follow-ups
let lastCitations = [];
let cmpBusy = false;
let currentConvId = null;   // null until the first question of a chat is saved

/* ---------------------------------------------------------
   Authentication
   --------------------------------------------------------- */

let token = localStorage.getItem("eka_token") || "";
let currentUser = null;

/** fetch() wrapper that attaches the bearer token and routes any 401 to
    the login screen (except the login call itself). */
function authFetch(url, opts) {
  opts = opts || {};
  const headers = Object.assign({}, opts.headers || {});
  if (token) headers.Authorization = "Bearer " + token;
  const p = fetch(url, Object.assign({}, opts, { headers }));
  p.then((res) => {
    if (res.status === 401 && !url.startsWith("/api/auth/login")) sessionExpired();
  }).catch(() => {});
  return p;
}

function showLogin(msg) {
  const err = $("#loginErr");
  if (err) {
    err.textContent = msg || "";
    err.hidden = !msg;
  }
  $("#loginScreen").hidden = false;
  const lay = $("#layout");
  if (lay) lay.hidden = true;
  setTimeout(() => $("#loginUser")?.focus(), 30);
}

function sessionExpired() {
  token = "";
  localStorage.removeItem("eka_token");
  currentUser = null;
  showLogin("Your session expired — sign in again.");
}

async function doLogin(ev) {
  ev.preventDefault();
  const err = $("#loginErr");
  err.hidden = true;
  const username = $("#loginUser").value.trim();
  const password = $("#loginPass").value;
  if (!username || !password) {
    err.textContent = "Enter a username and password.";
    err.hidden = false;
    return;
  }
  const btn = $("#loginBtn");
  btn.disabled = true;
  btn.textContent = "Signing in…";
  try {
    const res = await authFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Invalid username or password.");
    token = data.token;
    localStorage.setItem("eka_token", token);
    await enterApp(data.user);
  } catch (e) {
    err.textContent = e.message || "Sign-in failed — check the server.";
    err.hidden = false;
    $("#loginPass").value = "";
    $("#loginPass").focus();
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign in";
  }
}

/** Tail the UI to the signed-in user's role + department. */
function applyUserUI() {
  const isAdmin = currentUser && currentUser.role === "admin";
  document.body.classList.toggle("is-admin", Boolean(isAdmin));
  $("#ubAvatar").textContent = (currentUser.username || "A").charAt(0).toUpperCase();
  $("#ubName").textContent = currentUser.username || "user";
  $("#ubRole").textContent = isAdmin ? "Admin · full access" : (currentUser.department || "General") + " · Employee";

  const scopeNote = $("#scopeNote");
  scopeNote.hidden = Boolean(isAdmin);
  const deptSelEl = $("#dept");
  const sensSelEl = $("#sensitivity");
  deptSelEl.disabled = !isAdmin;
  sensSelEl.disabled = !isAdmin;
  if (!isAdmin) {
    deptSelEl.innerHTML = `<option>${escapeHtml(currentUser.department || "General")}</option>`;
    sensSelEl.value = "internal";
    scopeNote.innerHTML =
      `<span data-icon="info"></span>Scoped to <b>${escapeHtml(currentUser.department || "General")} + General</b> documents (Internal).`;
    hydrateIcons(scopeNote);
  }
}

async function enterApp(user) {
  currentUser = user;
  $("#loginScreen").hidden = true;
  $("#layout").hidden = false;
  applyUserUI();
  currentConvId = null;
  history = [];
  thread.innerHTML = "";
  newChat();
  setStreamingUI(false);
  await Promise.all([
    refreshLibrary(),
    refreshStats(),
    refreshChats(),
    currentUser.role === "admin" ? refreshUsers() : Promise.resolve(),
  ]);
  input.focus();
}

async function logout() {
  try {
    await authFetch("/api/auth/logout", { method: "POST" });
  } catch (e) { /* server may be offline — still sign out locally */ }
  token = "";
  localStorage.removeItem("eka_token");
  currentUser = null;
  showLogin();
}

/* ---------------------------------------------------------
   Toasts & confirm dialog
   --------------------------------------------------------- */

function toast(message, kind) {
  const root = $("#toastRoot");
  const node = el(
    "div",
    "toast " + (kind || "info"),
    `${iconEl(kind === "ok" ? "check" : kind === "err" ? "x" : "info").outerHTML}<div class="tt">${message}</div>`
  );
  node.querySelector(".tt").innerHTML = message;
  root.appendChild(node);

  const dismiss = () => {
    node.classList.add("out");
    setTimeout(() => node.remove(), 260);
  };
  const x = el("button", "x", "&times;");
  x.addEventListener("click", dismiss);
  node.appendChild(x);
  setTimeout(dismiss, 4200);
  return node;
}

function confirmDialog({ title, message, confirmLabel = "Remove", danger = true }) {
  return new Promise((resolve) => {
    const root = $("#modalRoot");
    root.innerHTML = "";
    const overlay = el("div", "overlay");

    const modal = el(
      "div",
      "modal",
      `
      <h3>${iconEl(danger ? "trash" : "info").outerHTML}<span>${escapeHtml(title)}</span></h3>
      <p>${escapeHtml(message)}</p>
      <div class="modal-actions">
        <button class="btn" data-act="cancel">Cancel</button>
        <button class="btn ${danger ? "danger" : "primary"}" data-act="ok">${escapeHtml(confirmLabel)}</button>
      </div>
      `
    );

    const done = (val) => {
      root.innerHTML = "";
      document.removeEventListener("keydown", onKey);
      resolve(val);
    };
    const onKey = (e) => {
      if (e.key === "Escape") done(false);
    };

    modal.addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]")?.getAttribute("data-act");
      if (act === "ok") done(true);
      else if (act === "cancel") done(false);
    });
    overlay.addEventListener("mousedown", (e) => {
      if (e.target === overlay) done(false);
    });

    overlay.appendChild(modal);
    root.appendChild(overlay);
    document.addEventListener("keydown", onKey);
    setTimeout(() => modal.querySelector('[data-act="ok"]').focus(), 30);
  });
}

/* ---------------------------------------------------------
   Library
   --------------------------------------------------------- */

const EXT_CLASS = { pdf: "t-pdf", doc: "t-doc", docx: "t-doc", txt: "t-txt", md: "t-md" };

function fileExt(name) {
  const m = String(name || "").match(/\.([a-z0-9]+)$/i);
  return m ? m[1].toLowerCase() : "file";
}

async function refreshLibrary() {
  try {
    const res = await authFetch("/api/documents", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const docs = await res.json();
    if (!Array.isArray(docs)) throw new Error("Invalid documents response");

    lib.innerHTML = "";
    libCount.textContent = docs.length;
    tabLibCount.textContent = docs.length;

    if (docs.length === 0) {
      lib.appendChild(
        el(
          "div",
          "lib-empty",
          `${iconEl("book").outerHTML}No documents indexed yet.<br/><span style="color:var(--text-4)">Upload a PDF, DOCX, TXT or MD file to get started.</span>`
        )
      );
      return;
    }

    populateDeptFilters();
    docs.forEach((d, idx) => {
      const rawTitle = String(d.title || "Untitled document");
      const title = escapeHtml(rawTitle);
      const filename = String(d.filename || "");
      const ext = fileExt(filename).toUpperCase();
      const extCls = EXT_CLASS[fileExt(filename)] || "";
      const nChunks = Number.isFinite(Number(d.n_chunks)) ? Number(d.n_chunks) : 0;
      const dept = escapeHtml(d.department || "General");
      const sens = String(d.sensitivity || "internal").toLowerCase();
      const sensLbl = sens === "confidential" ? "Confidential" : "Internal";
      const upDate = String(d.uploaded_at || "").slice(0, 10);
      const size = d.file_size == null ? Number.NaN : Number(d.file_size);

      const card = el("div", "doc-card");
      card.style.animationDelay = Math.min(idx * 30, 240) + "ms";
      card.dataset.previewId = d.id;
      card.dataset.previewTitle = title;
      card.dataset.dept = d.department || "General";
      card.dataset.sens = sens;
      card.dataset.title = rawTitle.toLowerCase();
      card.innerHTML = `
        <div class="doc-top">
          <span class="doc-ic ${extCls}">${ICONS.file}</span>
          <div class="doc-title">${title}<span class="ext">${escapeHtml(ext)}</span></div>
          <button class="doc-del" data-id="${escapeHtml(d.id)}" title="Remove document" aria-label="Remove ${title}">${ICONS.trash}</button>
          <label class="sel" title="Select for removal"><input type="checkbox" class="cb" data-id="${escapeHtml(d.id)}" aria-label="Select ${title}" /></label>
        </div>
        <div class="doc-meta">
          <span class="chip">${dept}</span>
          <span class="chip sens-${sens === "confidential" ? "conf" : "int"}"><i class="dot"></i>${sensLbl}</span>
          <span class="chip"><i>${nChunks}</i>&nbsp;chunk${nChunks === 1 ? "" : "s"}</span>
          ${upDate ? `<span class="chip">${escapeHtml(upDate)}</span>` : ""}
          ${Number.isFinite(size) ? `<span class="chip">${fmtBytes(size)}</span>` : ""}
        </div>
      `;
      lib.appendChild(card);
    });

    $$(".doc-del", lib).forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        void deleteDoc(btn.getAttribute("data-id"));
      });
    });
    $$(".doc-card", lib).forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".doc-del") || e.target.closest(".sel")) return;
        if (lib.classList.contains("selecting")) {
          const cb = card.querySelector(".cb");
          if (cb) {
            cb.checked = !cb.checked;
            updateBulkUI();
          }
          return;
        }
        void previewDoc(card.dataset.previewId);
      });
    });
    applyLibraryFilters();
  } catch (err) {
    console.error("Library loading failed:", err);
    lib.innerHTML = `<div class="lib-empty">${iconEl("info").outerHTML}Unable to load documents.</div>`;
    libCount.textContent = "—";
    tabLibCount.textContent = "—";
  }
}

async function deleteDoc(docId) {
  const card = lib.querySelector(`[data-id="${CSS.escape(docId)}"]`)?.closest(".doc-card");
  const title = card?.querySelector(".doc-title")?.childNodes[0]?.textContent || "this document";

  const ok = await confirmDialog({
    title: "Remove document",
    message: `Remove "${title}" from the library? Its chunks will be dropped and the index rebuilt.`,
    confirmLabel: "Remove",
  });
  if (!ok) return;

  card?.classList.add("deleting");
  try {
    const res = await authFetch("/api/documents/" + encodeURIComponent(docId), { method: "DELETE" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    toast(`Removed “${escapeHtml(title)}”.`, "ok");
    await refreshLibrary();
    await refreshStats();
  } catch (err) {
    console.error("Document deletion failed:", err);
    card?.classList.remove("deleting");
    toast("Unable to remove the document — check the server.", "err");
  }
}

/* ---------------------------------------------------------
   Library filters, search and bulk removal
   --------------------------------------------------------- */

const ALL_DEPTS = ["General", "HR", "Finance", "Legal", "Engineering", "Operations"];

function fmtBytes(n) {
  if (!Number.isFinite(Number(n)) || n < 0) return "";
  const v = Number(n);
  if (v < 1024) return v + " B";
  const units = ["KB", "MB", "GB"];
  let x = v / 1024;
  let i = 0;
  while (x >= 1024 && i < units.length - 1) { x /= 1024; i++; }
  return x.toFixed(x >= 10 ? 0 : 1) + " " + units[i];
}

function populateDeptFilters() {
  const sel = $("#filterDept");
  if (!sel || sel.dataset.seeded) return;
  sel.dataset.seeded = "1";
  const depts =
    currentUser && currentUser.role === "admin"
      ? ALL_DEPTS
      : currentUser
        ? [currentUser.department || "General", "General"]
        : ALL_DEPTS;
  [...new Set(depts)].forEach((d) => {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d;
    sel.appendChild(o);
  });
}

function applyLibraryFilters() {
  const q = ($("#libSearch").value || "").trim().toLowerCase();
  const dept = $("#filterDept").value;
  const sens = $("#filterSens").value;
  let visible = 0;
  $$(".doc-card", lib).forEach((card) => {
    const show =
      (!q || card.dataset.title.includes(q)) &&
      (!dept || card.dataset.dept === dept) &&
      (!sens || card.dataset.sens === sens);
    card.style.display = show ? "" : "none";
    if (show) visible++;
  });
  let noneEl = $(".lib-none", lib);
  if (visible === 0 && lib.querySelectorAll(".doc-card").length) {
    if (!noneEl) {
      noneEl = el("div", "lib-empty lib-none", `${iconEl("search").outerHTML}No documents match those filters.`);
      lib.appendChild(noneEl);
    }
  } else if (noneEl) noneEl.remove();
  updateBulkUI();
}

function exitSelectMode() {
  lib.classList.remove("selecting");
  const bar = $("#bulkBar");
  if (bar) bar.hidden = true;
  $$(".cb", lib).forEach((c) => (c.checked = false));
  const sa = $("#selAll");
  if (sa) { sa.checked = false; sa.indeterminate = false; }
}

function selectedIds() {
  return $$(".cb:checked", lib).map((c) => c.getAttribute("data-id")).filter(Boolean);
}

function updateBulkUI() {
  const bar = $("#bulkBar");
  if (!bar) return;
  const selecting = lib.classList.contains("selecting");
  bar.hidden = !selecting;
  if (!selecting) return;
  const ids = selectedIds();
  $("#bulkCount").textContent = ids.length + " selected";
  const visible = $$(".doc-card", lib).filter((c) => c.style.display !== "none");
  const selAll = $("#selAll");
  if (selAll && visible.length) {
    const checked = visible.map((c) => c.querySelector(".cb")?.checked);
    selAll.checked = checked.every(Boolean);
    selAll.indeterminate = !checked.every(Boolean) && checked.some(Boolean);
  }
}

async function bulkDelete() {
  const ids = selectedIds();
  if (!ids.length) return;
  const ok = await confirmDialog({
    title: `Remove ${ids.length} document${ids.length === 1 ? "" : "s"}?`,
    message: `This deletes ${ids.length} document${ids.length === 1 ? "" : "s"} and their chunks, then rebuilds the search index.`,
    confirmLabel: "Remove",
  });
  if (!ok) return;
  let removed = 0;
  let failed = 0;
  for (const id of ids) {
    const card = lib.querySelector(`.cb[data-id="${CSS.escape(id)}"]`)?.closest(".doc-card");
    card?.classList.add("deleting");
    try {
      const res = await authFetch("/api/documents/" + encodeURIComponent(id), { method: "DELETE" });
      if (res.ok) removed++;
      else failed++;
    } catch (e) { failed++; }
  }
  exitSelectMode();
  if (removed) toast(`Removed ${removed} document${removed === 1 ? "" : "s"}.`, "ok");
  if (failed) toast(`${failed} could not be removed — check permissions.`, "err");
  await refreshLibrary();
  await refreshStats();
}

/* ---------------------------------------------------------
   Team management (admin)
   --------------------------------------------------------- */

function seedUserForm() {
  const deptSel = $("#nuDept");
  if (!deptSel || deptSel.dataset.seeded) return;
  deptSel.dataset.seeded = "1";
  ALL_DEPTS.forEach((d) => {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d;
    deptSel.appendChild(o);
  });
  if (currentUser) deptSel.value = currentUser.department || "General";
}

async function refreshUsers() {
  const box = $("#users");
  if (!box || !currentUser || currentUser.role !== "admin") return;
  seedUserForm();
  try {
    const res = await authFetch("/api/users", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const rows = await res.json();
    box.innerHTML = "";
    const n = Array.isArray(rows) ? rows.length : 0;
    $("#userCount").textContent = n;
    $("#tabUserCount").textContent = n;
    if (!n) {
      box.appendChild(el("div", "lib-empty", "No users yet — add the first team member above."));
      return;
    }
    rows.forEach((u) => {
      const isSelf = currentUser && u.id === currentUser.id;
      const username = String(u.username || "?");
      const item = el("div", "user-row");
      item.innerHTML = `
        <div class="u-top">
          <span class="u-av">${escapeHtml(username.charAt(0).toUpperCase())}</span>
          <div class="u-name"><b>${escapeHtml(username)}</b><span>${u.active ? "active" : "disabled"}${isSelf ? " · you" : ""}</span></div>
          <select class="u-role" data-id="${escapeHtml(u.id)}" aria-label="Role for ${escapeHtml(username)}" ${isSelf ? "disabled" : ""}>
            <option value="employee" ${u.role === "employee" ? "selected" : ""}>Employee</option>
            <option value="admin" ${u.role === "admin" ? "selected" : ""}>Admin</option>
          </select>
        </div>
        <div class="u-bot">
          <select class="u-dept" data-id="${escapeHtml(u.id)}" aria-label="Department for ${escapeHtml(username)}">
            ${ALL_DEPTS.map((d) => `<option value="${escapeHtml(d)}" ${u.department === d ? "selected" : ""}>${escapeHtml(d)}</option>`).join("")}
          </select>
          <button class="mini-btn danger u-del" data-id="${escapeHtml(u.id)}" data-name="${escapeHtml(username)}" ${isSelf ? "disabled title=\"You can't remove yourself\"" : ""}>Remove</button>
        </div>`;
      box.appendChild(item);
    });
    $$(".u-role,.u-dept", box).forEach((sel) => {
      sel.addEventListener("change", () => {
        const id = sel.getAttribute("data-id");
        const payload = sel.classList.contains("u-role") ? { role: sel.value } : { department: sel.value };
        void patchUser(id, payload);
      });
    });
    $$(".u-del", box).forEach((btn) => {
      btn.addEventListener("click", () => void deleteUser(btn.getAttribute("data-id"), btn.getAttribute("data-name")));
    });
  } catch (err) {
    console.error("Users loading failed:", err);
    box.innerHTML = `<div class="lib-empty">${iconEl("info").outerHTML}Unable to load users.</div>`;
  }
}

async function patchUser(id, payload) {
  try {
    const res = await authFetch("/api/users/" + encodeURIComponent(id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "update failed");
    toast("User updated.", "ok");
    void refreshUsers();
  } catch (e) {
    toast("Couldn't update user — " + (e.message || "error"), "err");
    void refreshUsers();
  }
}

async function deleteUser(id, name) {
  const ok = await confirmDialog({
    title: "Remove user",
    message: `Remove “${escapeHtml(name || "this user")}”? They will no longer be able to sign in.`,
    confirmLabel: "Remove",
  });
  if (!ok) return;
  try {
    const res = await authFetch("/api/users/" + encodeURIComponent(id), { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "delete failed");
    toast("User removed.", "ok");
    void refreshUsers();
  } catch (e) {
    toast("Couldn't remove user — " + (e.message || "error"), "err");
    void refreshUsers();
  }
}

async function addUser() {
  const username = $("#nuName").value.trim();
  const password = $("#nuPass").value;
  if (!username || password.length < 4) {
    toast("Username + password of at least 4 characters required.", "err");
    return;
  }
  const btn = $("#nuAdd");
  btn.disabled = true;
  try {
    const res = await authFetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, role: $("#nuRole").value, department: $("#nuDept").value }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "create failed");
    $("#nuName").value = "";
    $("#nuPass").value = "";
    toast(`Added ${escapeHtml(username)}.`, "ok");
    void refreshUsers();
  } catch (e) {
    toast("Couldn't add user — " + (e.message || "error"), "err");
  } finally {
    btn.disabled = false;
  }
}

/* ---------------------------------------------------------
   Conversations (persisted chat history)
   --------------------------------------------------------- */

const EMPTY_STATE_HTML = `
<div class="empty-state" id="emptyState">
  <div class="empty-mark" data-icon="spark"></div>
  <h2>Ask your documents</h2>
  <p>
    Every answer is built from the passages that actually support it —
    no guessing. Upload a policy, contract or handbook, then ask anything.<br />
    Tap the <b>[n]</b> markers to jump to the exact source in the evidence rail.
  </p>
  <div class="sugg" id="suggestions">
    <button type="button" data-q="Summarise the key policies that apply to employees, with the document each comes from.">
      <span data-icon="spark"></span>Summarise the main policies in the library
    </button>
    <button type="button" data-q="What do the documents say about confidentiality and data classification?">
      <span data-icon="spark"></span>Confidentiality &amp; data classification
    </button>
    <button type="button" data-q="Find anything that mentions annual leave, entitlements or carry-over.">
      <span data-icon="spark"></span>Annual leave entitlements
    </button>
  </div>
</div>`;

function showEmptyState() {
  if ($("#emptyState")) return;
  const node = el("div", null, EMPTY_STATE_HTML);
  thread.appendChild(node);
  hydrateIcons(node);
  $$("#suggestions button", node).forEach((b) => {
    b.addEventListener("click", () => {
      input.value = b.getAttribute("data-q");
      autoGrow();
      input.focus();
    });
  });
}

function newChat() {
  if (streaming) return;
  currentConvId = null;
  history = [];
  thread.innerHTML = "";
  showEmptyState();
  renderEvidence([]);
  void refreshChats();
  setView("ask");
}

async function refreshChats() {
  try {
    const res = await authFetch("/api/conversations", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const convs = await res.json();
    chats.innerHTML = "";
    tabChatCount.textContent = Array.isArray(convs) ? convs.length : "—";
    if (!Array.isArray(convs) || convs.length === 0) {
      chats.appendChild(el("div", "lib-empty", "No saved chats yet — your Q&A will appear here."));
      return;
    }
    convs.forEach((c) => {
      const n = Number(c.message_count) || 0;
      const item = el("div", "chat-item" + (currentConvId === c.id ? " active" : ""));
      item.innerHTML = `
        <div class="chat-t">
          <span class="chat-ic">${ICONS.chat}</span>
          <span class="chat-title">${escapeHtml(c.title || "New chat")}</span>
          <button class="chat-del" title="Delete chat" aria-label="Delete chat">${ICONS.x}</button>
        </div>
        <div class="chat-meta">${n} message${n === 1 ? "" : "s"} · ${escapeHtml(String(c.updated_at || "").slice(0, 16).replace("T", " "))}</div>
      `;
      const del = item.querySelector(".chat-del");
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        void deleteChat(c.id, c.title || "this chat");
      });
      item.addEventListener("click", () => {
        if (streaming) { toast("Wait for the current answer to finish.", "info"); return; }
        void openChat(c.id);
      });
      chats.appendChild(item);
    });
  } catch (err) {
    console.error("Chats loading failed:", err);
    chats.innerHTML = `<div class="lib-empty">Unable to load chats.</div>`;
    tabChatCount.textContent = "—";
  }
}

async function deleteChat(convId, title) {
  const ok = await confirmDialog({
    title: "Delete chat",
    message: `Delete "${title}" and all of its messages? This cannot be undone.`,
    confirmLabel: "Delete",
  });
  if (!ok) return;
  try {
    const res = await authFetch("/api/conversations/" + encodeURIComponent(convId), { method: "DELETE" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    if (currentConvId === convId) newChat();
    else void refreshChats();
    toast("Chat deleted.", "ok");
  } catch (err) {
    console.error("Chat deletion failed:", err);
    toast("Unable to delete the chat.", "err");
  }
}

async function openChat(convId) {
  try {
    const res = await authFetch("/api/conversations/" + encodeURIComponent(convId), { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const conv = await res.json();
    currentConvId = conv.id;
    history = [];
    thread.innerHTML = "";
    const msgs = Array.isArray(conv.messages) ? conv.messages : [];
    let lastUser = "";
    let lastCitations = [];
    msgs.forEach((m) => {
      if (m.role === "user") {
        lastUser = String(m.content || "");
        addUserMsg(lastUser);
        history.push({ role: "user", content: lastUser });
      } else if (m.role === "assistant") {
        let citations = parseCitations(m.citations);
        lastCitations = citations;
        const wrap = addAssistantShell();
        renderAssistantStatic(wrap, String(m.content || ""), citations, Number(m.groundedness) || null, lastUser);
        history.push({ role: "assistant", content: String(m.content || "") });
        if (m.id) attachFeedback(wrap.body.querySelector(".msg-foot"), m.id, Number(m.feedback) || 0);
      }
    });
    if (lastUser) lastQuestion = lastUser;
    renderEvidence(lastCitations);
    scrollThread(true);
    void refreshChats();
    input.focus();
  } catch (err) {
    console.error("Open chat failed:", err);
    toast("Unable to open that chat.", "err");
  }
}

function parseCitations(raw) {
  if (Array.isArray(raw)) return raw;
  if (!raw) return [];
  try { const v = JSON.parse(raw); return Array.isArray(v) ? v : []; }
  catch (e) { return []; }
}

function renderAssistantStatic(wrap, content, citations, groundedness, question) {
  const { bubble, body } = wrap;
  const tag =
    groundedness != null && Number.isFinite(groundedness)
      ? `<div style="margin-top:10px"><span class="tag ${groundedness >= 0.35 ? "g-high" : "g-low"}"><span class="dot"></span>Grounded · ${Math.round(groundedness * 100)}%</span></div>`
      : "";
  bubble.innerHTML = renderAnswerMarkup(content, citations) + tag;
  const foot = el("div", "msg-foot");
  const copyBtn = el("button", "mini-btn", ICONS.copy + "<span>Copy answer</span>");
  copyBtn.addEventListener("click", () => copyText(content, copyBtn));
  foot.appendChild(copyBtn);
  const dlBtn = el("button", "mini-btn", ICONS.download + "<span>Download .md</span>");
  dlBtn.addEventListener("click", () => exportAnswer(question || "Chat export", content, citations));
  foot.appendChild(dlBtn);
  if (citations.length) {
    const chip = el("span", "mini-btn", ICONS.layers + `<span>${citations.length} source${citations.length === 1 ? "" : "s"}</span>`);
    chip.style.cursor = "default";
    foot.appendChild(chip);
  }
  body.appendChild(foot);
  if (!streaming) addFollowUps(body, citations);
}

async function persistAskPair(question, answer, citations, groundedness) {
  if (!currentConvId) {
    const res = await authFetch("/api/conversations", { method: "POST" });
    if (!res.ok) throw new Error("create conversation");
    currentConvId = (await res.json()).id;
  }
  await saveMessage("user", question, null, null);
  const assistantMsgId = await saveMessage("assistant", answer, citations, groundedness);
  void refreshChats();
  return assistantMsgId;
}

async function saveMessage(role, content, citations, groundedness) {
  const res = await fetch(`/api/conversations/${encodeURIComponent(currentConvId)}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      role,
      content,
      citations: citations || null,
      groundedness: groundedness ?? null,
    }),
  });
  if (!res.ok) throw new Error("save message");
  return (await res.json()).id;
}

function attachFeedback(foot, msgId, initial = 0) {
  const row = el("span", "fb-row");
  const mk = (value, icon, label) => {
    const b = el("button", "mini-btn fb" + (initial === value ? " on" : ""), icon + `<span>${label}</span>`);
    b.dataset.v = String(value);
    b.setAttribute("aria-pressed", initial === value ? "true" : "false");
    b.addEventListener("click", async () => {
      const cur = b.classList.contains("on") ? 0 : value;
      $$(".fb", row).forEach((x) => x.classList.toggle("on", x === b && cur !== 0));
      b.setAttribute("aria-pressed", String(cur !== 0));
      try {
        const res = await fetch(`/api/messages/${encodeURIComponent(msgId)}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: cur }),
        });
        if (!res.ok) throw new Error("feedback save");
        toast(cur !== 0 ? (value > 0 ? "Thanks — glad it helped!" : "Thanks — we'll improve.") : "Feedback cleared.", "ok");
      } catch (err) {
        toast("Couldn't save feedback.", "err");
      }
    });
    return b;
  };
  row.appendChild(mk(1, ICONS.thumbUp, "Helpful"));
  row.appendChild(mk(-1, ICONS.thumbDown, "Not"));
  foot.appendChild(row);
}

function exportAnswer(question, answer, citations) {
  const lines = [`# ${question}`, "", answer, ""];
  if (Array.isArray(citations) && citations.length) {
    lines.push("## Sources", "");
    citations.forEach((c, i) => {
      const trail = Array.isArray(c.section_trail)
        ? c.section_trail.filter(Boolean).join(" > ")
        : "";
      const pages =
        c.page_start != null
          ? (c.page_start === c.page_end ? `p. ${c.page_start}` : `pp. ${c.page_start}–${c.page_end}`)
          : "";
      lines.push(`${i + 1}. **${c.title || "Document"}**${trail ? ` — ${trail}` : ""}${pages ? ` (${pages})` : ""}`, "", String(c.text || ""), "");
    });
  }
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "answer.md";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

async function previewDoc(docId) {
  try {
    const res = await authFetch("/api/documents/" + encodeURIComponent(docId) + "/preview", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    const doc = data.document || {};
    const chunks = Array.isArray(data.chunks) ? data.chunks : [];
    const root = $("#modalRoot");
    root.innerHTML = "";
    const overlay = el("div", "overlay");
    const modal = el(
      "div",
      "modal modal-wide",
      `
      <h3>${iconEl("file").outerHTML}<span>${escapeHtml(doc.title || "Document")}</span></h3>
      <div class="preview-meta">
        <span class="chip">${escapeHtml(doc.department || "General")}</span>
        <span class="chip">${escapeHtml(doc.filename || "")}</span>
        <span class="chip">${chunks.length} chunk${chunks.length === 1 ? "" : "s"}</span>
        <span class="chip">${escapeHtml(String(doc.uploaded_at || "").slice(0, 16).replace("T", " "))}</span>
      </div>
      <div class="preview-body">
        ${chunks.length === 0 ? `<div class="cmp-none">No text chunks in this document.</div>` : ""}
        ${chunks.map((c, i) => {
          let trail = [];
          try { trail = Array.isArray(c.section_trail) ? c.section_trail : JSON.parse(c.section_trail || "[]"); } catch (e) { /* keep empty */ }
          const pages =
            c.page_start != null
              ? (c.page_start === c.page_end ? `p. ${c.page_start}` : `pp. ${c.page_start}–${c.page_end}`)
              : "";
          return `<div class="preview-chunk">
            <div class="pc-head"><span class="pc-num">#${i + 1}</span><span class="pc-trail">${trail.filter(Boolean).map((x) => escapeHtml(x)).join(" › ") || escapeHtml(doc.title || "")}</span>${pages ? `<span class="pc-page">${escapeHtml(pages)}</span>` : ""}</div>
            <div class="pc-text">${escapeHtml(c.text || "")}</div>
          </div>`;
        }).join("")}
      </div>
      <div class="modal-actions"><button class="btn" data-act="cancel">Close</button></div>
      `
    );
    const done = () => {
      root.innerHTML = "";
      document.removeEventListener("keydown", onKey);
    };
    const onKey = (e) => { if (e.key === "Escape") done(); };
    modal.addEventListener("click", (e) => { if (e.target.closest('[data-act="cancel"]')) done(); });
    overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) done(); });
    overlay.appendChild(modal);
    root.appendChild(overlay);
    document.addEventListener("keydown", onKey);
  } catch (err) {
    console.error("Preview failed:", err);
    toast("Unable to preview that document.", "err");
  }
}

/* ---------------------------------------------------------
   Statistics
   --------------------------------------------------------- */

async function refreshStats() {
  try {
    const res = await authFetch("/api/stats", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const s = await res.json();
    statDocs.textContent = fmtNum(s.documents);
    statChunks.textContent = fmtNum(s.chunks);
    statVectors.textContent = fmtNum(s.faiss_vectors);
  } catch (err) {
    console.error("Stats loading failed:", err);
    statDocs.textContent = statChunks.textContent = statVectors.textContent = "—";
  }
}

/* ---------------------------------------------------------
   Upload
   --------------------------------------------------------- */

const DROP_IDLE = { cls: "", b: "Upload a document", s: "Drop files here, or click to browse" };

function setDropState(kind, title, sub) {
  drop.classList.remove("state-ok", "state-err", "state-busy");
  if (kind) drop.classList.add("state-" + kind);
  const label = $("#dropLabel");
  if (label) {
    label.innerHTML = `<b>${escapeHtml(title || "")}</b><span>${escapeHtml(sub || "")}</span>`;
  }
}

function dropIdle() {
  setTimeout(() => setDropState(null, DROP_IDLE.b, DROP_IDLE.s), 2600);
}

/* --- multi-file upload queue ---------------------------------------- */

function addQueueRow(name) {
  const q = $("#upQueue");
  if (!q) return null;
  q.hidden = false;
  const row = el("div", "up-row");
  row.innerHTML = `
    <span class="up-ic" data-icon="file"></span>
    <span class="up-name">${escapeHtml(name)}</span>
    <span class="up-st">Queued…</span>`;
  hydrateIcons(row);
  q.appendChild(row);
  return row;
}

function setRow(row, state, text) {
  if (!row) return;
  row.classList.remove("ok", "err", "dup", "busy");
  if (state) row.classList.add(state);
  const st = row.querySelector(".up-st");
  if (st) st.textContent = text;
}

async function uploadFile(file, row) {
  if (!file) return { status: "skip" };
  const fd = new FormData();
  fd.append("file", file);
  fd.append("department", deptSel.value || "General");
  fd.append("sensitivity", sensSel.value || "internal");

  setRow(row, "busy", "Uploading…");
  setDropState("busy", `Indexing ${file.name}…`, "Reading, chunking and embedding — one moment");
  try {
    const res = await authFetch("/api/documents", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || "HTTP " + res.status);
    if (data.status === "duplicate") {
      setRow(row, "dup", "Already indexed");
      return { status: "duplicate", data };
    }
    setRow(row, "ok", `Indexed · ${data.chunks_indexed ?? "?"} chunks`);
    return { status: "ok", data };
  } catch (err) {
    setRow(row, "err", err.message || "Failed");
    return { status: "err", message: err.message || "Upload failed" };
  }
}

async function enqueueFiles(fileList) {
  const files = Array.from(fileList || []).filter((f) => f && f.size > 0);
  if (!files.length) return;
  drop.classList.remove("state-ok", "state-err");
  let ok = 0;
  let dup = 0;
  let errs = 0;
  let firstErr = "";
  for (const f of files) {
    const row = addQueueRow(f.name);
    const r = await uploadFile(f, row);
    if (r.status === "ok") ok++;
    else if (r.status === "duplicate") dup++;
    else { errs++; firstErr = firstErr || r.message; }
  }
  fileInput.value = "";
  dropIdle();
  if (ok) toast(`Indexed ${ok} file${ok === 1 ? "" : "s"}${dup ? ` (${dup} duplicate${dup === 1 ? "" : "s"} skipped)` : ""}.`, "ok");
  else if (dup && !errs) toast(`${dup} duplicate${dup === 1 ? "" : "s"} skipped — already in the library.`, "info");
  else if (errs) toast("Upload failed: " + escapeHtml(firstErr || "unknown error"), "err");
  if (ok || errs) {
    await refreshLibrary();
    await refreshStats();
  }
  setTimeout(() => {
    const q = $("#upQueue");
    if (q && !q.querySelector(".busy")) {
      q.innerHTML = "";
      q.hidden = true;
    }
  }, 6000);
}

fileInput.addEventListener("change", (e) => {
  void enqueueFiles(e.target.files);
});

let dragDepth = 0;
drop.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragDepth += 1;
  drop.classList.add("drag");
});
drop.addEventListener("dragover", (e) => e.preventDefault());
drop.addEventListener("dragleave", () => {
  dragDepth -= 1;
  if (dragDepth <= 0) {
    dragDepth = 0;
    drop.classList.remove("drag");
  }
});
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  drop.classList.remove("drag");
  void enqueueFiles(e.dataTransfer.files);
});

// The drop zone is a native <label for="fileInput">, so clicking it opens
// the picker with zero JavaScript. Enter/Space still need a handler because
// labels aren't keyboard-activated natively.
drop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

$("#libRefresh").addEventListener("click", () => {
  void refreshLibrary();
  void refreshStats();
});

/* Library tools: filter, search, bulk selection */
$("#libSearch").addEventListener("input", applyLibraryFilters);
$("#filterDept").addEventListener("change", applyLibraryFilters);
$("#filterSens").addEventListener("change", applyLibraryFilters);

$("#libSel").addEventListener("click", () => {
  const on = lib.classList.toggle("selecting");
  if (!on) exitSelectMode();
  else updateBulkUI();
});

$("#bulkClear").addEventListener("click", () => exitSelectMode());
$("#bulkDelete").addEventListener("click", () => void bulkDelete());

$("#selAll").addEventListener("change", (e) => {
  $$(".doc-card", lib)
    .filter((c) => c.style.display !== "none")
    .forEach((c) => {
      const cb = c.querySelector(".cb");
      if (cb) cb.checked = e.target.checked;
    });
  updateBulkUI();
});

lib.addEventListener("change", (e) => {
  if (e.target.classList && e.target.classList.contains("cb")) updateBulkUI();
});

/* Auth: login form + sign out */
$("#loginForm").addEventListener("submit", (e) => void doLogin(e));
$("#logoutBtn").addEventListener("click", () => void logout());

/* Team admin wiring */
$("#nuAdd").addEventListener("click", () => void addUser());
$("#nuName").addEventListener("keydown", (e) => { if (e.key === "Enter") void addUser(); });
$("#nuPass").addEventListener("keydown", (e) => { if (e.key === "Enter") void addUser(); });

/* ---------------------------------------------------------
   Markdown + citations rendering
   --------------------------------------------------------- */

function renderAnswerMarkup(text, citations) {
  let t = String(text || "");
  // Unicode citation brackets 【1】 -> [1]
  t = t.replace(/【\s*(\d+)\s*】/g, "[$1]");

  let html;
  try {
    html = marked.parse(t, { breaks: true, gfm: true });
  } catch (err) {
    console.warn("Markdown parse failed, falling back to plain text:", err);
    html = escapeHtml(t).replace(/\n/g, "<br/>");
  }
  if (window.DOMPurify) {
    html = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
  } else {
    // Safety net: never inject un-sanitized HTML into the page.
    html = escapeHtml(t).replace(/\n/g, "<br/>");
  }

  const list = Array.isArray(citations) ? citations : [];
  html = html.replace(/\[(\d+)\]/g, (m, n) => {
    const has = list.some((c) => String(c.marker) === n);
    return has
      ? `<span class="cite" role="button" tabindex="0" data-n="${escapeHtml(n)}" title="Show source [${escapeHtml(n)}]">${escapeHtml(n)}</span>`
      : m;
  });
  return html;
}

/* ---------------------------------------------------------
   Evidence rail
   --------------------------------------------------------- */

/* ---- query-term highlighting for evidence passages ---- */

const TERM_STOPWORDS = new Set([
  "about", "after", "again", "also", "been", "before", "being", "between", "does",
  "from", "have", "into", "more", "most", "other", "some", "such", "than", "that",
  "their", "them", "then", "there", "these", "they", "this", "those", "through",
  "what", "when", "where", "which", "while", "with", "will", "would", "your",
  "tell", "info", "find", "like", "just", "tell", "does", "there", "document",
]);

function queryTerms(q) {
  return [...new Set(String(q || "")
    .toLowerCase()
    .split(/[^a-z0-9-]+/i)
    .filter((w) => w.length > 3 && !TERM_STOPWORDS.has(w)))]
    .slice(0, 8);
}

function escapeReg(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Highlight query terms inside already-escaped HTML. */
function hl(escapedHtmlText, terms) {
  if (!terms || !terms.length) return escapedHtmlText;
  return escapedHtmlText.replace(
    new RegExp(`(${terms.map(escapeReg).join("|")})`, "gi"),
    "<mark>$1</mark>"
  );
}

function renderEvidence(citations) {
  lastCitations = Array.isArray(citations) ? citations : [];
  railBody.innerHTML = "";
  const terms = queryTerms(lastQuestion);

  if (lastCitations.length === 0) {
    evCount.hidden = true;
    railSub.textContent = "No passages were cited by the last answer.";
    railBody.appendChild(
      el(
        "div",
        "ev-empty",
        `${ICONS.layers}<span>Ask a question to see the exact passages your answer is grounded in, with page and section context.</span>`
      )
    );
    return;
  }

  evCount.hidden = false;
  evCount.textContent = lastCitations.length;
  railSub.textContent = lastCitations.length + (lastCitations.length === 1 ? " passage" : " passages") + " cited by the last answer";

  lastCitations.forEach((c, i) => {
    const marker = escapeHtml(c.marker);
    const title = escapeHtml(c.title || "Document");
    const trail = Array.isArray(c.section_trail)
      ? c.section_trail.filter(Boolean).map((x) => escapeHtml(x)).join(" › ")
      : "";
    const pages =
      c.page_start != null
        ? (c.page_start === c.page_end ? "p." + escapeHtml(c.page_start) : "pp." + escapeHtml(c.page_start) + "–" + escapeHtml(c.page_end))
        : "";
    const text = String(c.text || "");
    const full = text.length > 300;

    const card = el("div", "evi-card");
    card.id = "evi-" + marker;
    card.style.animationDelay = Math.min(i * 40, 300) + "ms";
    card.innerHTML = `
      <div class="evi-top">
        <span class="evi-num">${marker}</span>
        <span class="evi-title">${title}</span>
      </div>
      ${trail ? `<div class="evi-trail">${ICONS.page}${trail}</div>` : ""}
      <div class="evi-text">${hl(escapeHtml(full ? text.slice(0, 300) : text), terms)}${full ? "…" : ""}</div>
      ${full ? `<button class="evi-more">Show full passage</button>` : ""}
      <div class="evi-foot">${pages ? `${ICONS.page}${pages}` : ""}${ICONS.layers}cited in answer</div>
    `;

    const more = card.querySelector(".evi-more");
    if (more) {
      more.addEventListener("click", () => {
        const open = card.classList.toggle("open");
        more.textContent = open ? "Show less" : "Show full passage";
        const textEl = card.querySelector(".evi-text");
        if (open) textEl.innerHTML = hl(escapeHtml(text), terms);
        else textEl.innerHTML = hl(escapeHtml(text.slice(0, 300)), terms) + "…";
      });
    }

    railBody.appendChild(card);
  });
}

function highlightCitation(n) {
  $$(".evi-card", railBody).forEach((c) => c.classList.remove("active"));
  const card = document.getElementById("evi-" + n);
  if (!card) return;
  card.classList.add("active");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  card.classList.remove("flash");
  // restart the flash animation
  void card.offsetWidth;
  card.classList.add("flash");
}

/* ---------------------------------------------------------
   Messages / chat DOM
   --------------------------------------------------------- */

function scrollThread(smooth) {
  thread.scrollTo({ top: thread.scrollHeight, behavior: smooth ? "smooth" : "auto" });
}

function removeEmptyState() {
  emptyState?.remove();
}

function addUserMsg(text) {
  removeEmptyState();
  const wrap = el("div", "msg user");
  wrap.innerHTML = `
    <div class="avatar">${ICONS.user}</div>
    <div class="msg-body">
      <div class="role-line"><span class="who">You</span><span>· ${nowTime()}</span></div>
      <div class="bubble">${escapeHtml(text)}</div>
    </div>
  `;
  thread.appendChild(wrap);
  scrollThread();
  return wrap;
}

function addAssistantShell() {
  removeEmptyState();
  const wrap = el("div", "msg assistant");
  const body = el("div", "msg-body");
  const role = el("div", "role-line", `<span class="who">Assistant</span><span>· ${nowTime()}</span>`);
  const bubble = el("div", "bubble");
  body.append(role, bubble);
  wrap.append(el("div", "avatar", ICONS.spark), body);
  thread.appendChild(wrap);
  return { wrap, bubble, body };
}

function addTyping(shell, label) {
  shell.bubble.innerHTML =
    `<div class="typing-status"><span class="spin"></span><span class="typing-label">${escapeHtml(label || "Retrieving passages…")}</span></div>`;
  scrollThread();
}

function setTypingLabel(shell, text) {
  const node = shell && shell.bubble ? shell.bubble.querySelector(".typing-label") : null;
  if (node) node.textContent = text;
}

/* ---------------------------------------------------------
   Copy to clipboard
   --------------------------------------------------------- */

async function copyText(text, btn) {
  let ok = false;
  try {
    await navigator.clipboard.writeText(text);
    ok = true;
  } catch (err) {
    // Fallback for older browsers / non-secure contexts
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      ok = document.execCommand("copy");
      ta.remove();
    } catch (e2) {
      ok = false;
    }
  }
  if (ok && btn) {
    const prev = btn.innerHTML;
    btn.innerHTML = ICONS.check + "<span>Copied</span>";
    btn.classList.add("ok");
    setTimeout(() => {
      btn.innerHTML = prev;
      btn.classList.remove("ok");
    }, 1600);
  } else {
    toast("Couldn't copy to clipboard.", "err");
  }
}

/* ---------------------------------------------------------
   Ask (SSE streaming)
   --------------------------------------------------------- */

function setStreamingUI(on) {
  streaming = on;
  sendBtn.disabled = on;
  input.disabled = on;
  stopBtn.hidden = !on;
  composerHint.textContent = on ? "Answering — you can stop anytime" : view === "ask" ? "↵ send · shift+↵ newline" : "↵ run comparison";
}

function clearThreadErrorCard() {
  $$(".msg.err-msg").forEach((n) => n.remove());
}

function addErrorCard(message) {
  clearThreadErrorCard();
  const wrap = el("div", "msg assistant err-msg");
  const body = el("div", "msg-body");
  const bubble = el(
    "div",
    "bubble",
    `<div style="margin:0 0 6px;color:var(--danger);font-weight:600">${ICONS.info} Generation failed</div><div>${escapeHtml(message || "Unknown error")}</div>`
  );
  const retry = el("button", "mini-btn", ICONS.refresh + "<span>Try again</span>");
  retry.addEventListener("click", () => {
    input.value = lastQuestion;
    input.focus();
    wrap.remove();
  });
  const foot = el("div", "msg-foot");
  foot.appendChild(retry);
  const hint = el("div", "note-line", "Check the server terminal for the full traceback.");
  body.append(bubble, foot, hint);
  wrap.append(el("div", "avatar", ICONS.spark), body);
  thread.appendChild(wrap);
  scrollThread();
  setStreamingUI(false);
}

let lastQuestion = "";

async function ask() {
  if (streaming) return;
  const q = input.value.trim();
  if (!q) return;

  lastQuestion = q;
  input.value = "";
  input.style.height = "auto";

  if (view === "compare") {
    void runCompare(q);
    return;
  }

  addUserMsg(q);

  const shell = addAssistantShell();
  addTyping(shell, "Retrieving passages…");
  scrollThread();

  abortCtrl = new AbortController();
  setStreamingUI(true);

  const state = {
    started: false,
    acc: "",
    finalPayload: null,
    retrieved: [],
    aborted: false,
    shell,
  };

  try {
    const res = await authFetch("/api/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, history }),
      signal: abortCtrl.signal,
    });

    if (!res.ok) {
      let msg = "HTTP " + res.status;
      try {
        const d = await res.json();
        msg = d.detail || d.message || msg;
      } catch (_) { /* not JSON */ }
      throw new Error(msg);
    }
    if (!res.body) throw new Error("Streaming response body is unavailable.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const events = buf.split(/\r?\n\r?\n/);
      buf = events.pop() || "";
      for (const evt of events) processSSEEvent(evt, state);
    }
    buf += decoder.decode();
    if (buf.trim()) processSSEEvent(buf.trim(), state);

    finishAnswer(state, q, false);
  } catch (err) {
    if (err && err.name === "AbortError") {
      state.aborted = true;
      finishAnswer(state, q, true);
      return;
    }
    console.error("Ask failed:", err);
    shell.wrap.remove();
    addErrorCard(err.message || "Unknown error");
  } finally {
    abortCtrl = null;
    if (!document.querySelector(".err-msg")) setStreamingUI(false);
  }
}

function processSSEEvent(rawEvent, state) {
  if (!rawEvent || !rawEvent.trim()) return;
  const lines = rawEvent.split(/\r?\n/);
  const eventType = (lines.find((l) => l.startsWith("event:")) || "").replace(/^event:\s*/, "").trim();
  const rawData = (lines.find((l) => l.startsWith("data:")) || "").replace(/^data:\s*/, "").trim();
  if (!rawData) return;

  let data;
  try {
    data = JSON.parse(rawData);
  } catch (err) {
    console.error("Invalid SSE JSON:", rawData, err);
    return;
  }

  if (eventType === "retrieved") {
    state.retrieved = Array.isArray(data.retrieved) ? data.retrieved : [];
    setTypingLabel(state.shell, "Writing answer…");
    return;
  }

  if (eventType === "token") {
    const text = String(data.text || "");
    if (!state.started) {
      state.started = true;
      state.shell.bubble.innerHTML = '<span class="cursor-blink"></span>';
    }
    state.acc += text;
    state.shell.bubble.innerHTML =
      renderAnswerMarkup(state.acc, []) + '<span class="cursor-blink"></span>';
    scrollThread();
    return;
  }

  if (eventType === "done") {
    state.finalPayload = data;
    return;
  }

  if (eventType === "error") {
    throw new Error(data.message || "Generation failed");
  }
}

/* ---- follow-up suggestions ------------------------------------------- */

function addFollowUps(body, citations) {
  if (!body || !Array.isArray(citations) || !citations.length) return;
  const seen = new Set();
  const ideas = [];
  citations.forEach((c) => {
    const trail = Array.isArray(c.section_trail) ? c.section_trail.filter(Boolean) : [];
    const head = trail[trail.length - 1] || "";
    const doc = String(c.title || "");
    const key = doc + "|" + head;
    if (seen.has(key) || ideas.length >= 2 || !(head || doc)) return;
    seen.add(key);
    ideas.push({
      label: String(head || doc).slice(0, 46),
      q: head ? `Tell me more about ${head} in ${doc}` : `Tell me more about ${doc}`,
    });
  });
  if (!ideas.length) return;
  const row = el("div", "follow-row");
  const lbl = el("span", "follow-lbl", "Ask a follow-up");
  row.appendChild(lbl);
  ideas.forEach((idea) => {
    const b = el("button", "mini-btn follow", ICONS.spark + "<span>" + escapeHtml(idea.label) + "</span>");
    b.addEventListener("click", () => {
      if (streaming) return;
      input.value = idea.q;
      autoGrow();
      input.focus();
      void ask();
    });
    row.appendChild(b);
  });
  body.appendChild(row);
}

function finishAnswer(state, q, wasAborted) {
  const bubble = state.shell.bubble;
  const finalPayload = state.finalPayload || {};
  const citations = Array.isArray(finalPayload.citations) ? finalPayload.citations : [];
  const acc = state.acc;

  let finalAnswer;
  if (wasAborted) {
    finalAnswer = acc;
  } else {
    finalAnswer = String(finalPayload.answer ?? acc ?? "");
    if (!finalAnswer && !acc) finalAnswer = "";
  }

  const groundedness = Number(finalPayload.groundedness ?? 0);
  const refused = Boolean(finalPayload.refused);
  const tagCls = refused ? "g-refused" : groundedness >= 0.35 ? "g-high" : "g-low";
  const tagLbl = refused
    ? "Not in documents"
    : `Grounded · ${Math.round(groundedness * 100)}%`;

  if (!state.started && !finalAnswer) {
    bubble.innerHTML = wasAborted
      ? "<em style='color:var(--text-4)'>Generation stopped before any text was produced.</em>"
      : "<em style='color:var(--text-4)'>The assistant returned an empty answer.</em>";
  } else {
    const markup =
      renderAnswerMarkup(finalAnswer, wasAborted ? [] : citations) +
      `<div style="margin-top:10px"><span class="tag ${tagCls}" title="${refused ? "The model judged that the retrieved passages do not answer this question." : "Fraction of answer vocabulary found in the retrieved passages."}"><span class="dot"></span>${escapeHtml(tagLbl)}</span></div>`;

    bubble.innerHTML = markup;
  }

  if (wasAborted) {
    const note = el("div", "note-line", "Generation stopped — the answer above is incomplete.");
    bubble.appendChild(note);
  } else {
    renderEvidence(citations);

    history.push({ role: "user", content: q });
    const clean = finalAnswer.replace(/\u0000/g, "");
    history.push({ role: "assistant", content: clean });
  }

  /* message footer: copy + export + citation hint */
  const foot = el("div", "msg-foot");
  const copyBtn = el("button", "mini-btn", ICONS.copy + "<span>Copy answer</span>");
  copyBtn.addEventListener("click", () => copyText(finalAnswer, copyBtn));
  foot.appendChild(copyBtn);
  const dlBtn = el("button", "mini-btn", ICONS.download + "<span>Download .md</span>");
  dlBtn.addEventListener("click", () => exportAnswer(q, finalAnswer, citations));
  foot.appendChild(dlBtn);
  if (citations.length) {
    const chip = el(
      "span",
      "mini-btn",
      ICONS.layers + `<span>${citations.length} source${citations.length === 1 ? "" : "s"} · click [n] to inspect</span>`
    );
    chip.style.cursor = "default";
    foot.appendChild(chip);
  }
  state.shell.body.appendChild(foot);
  if (!wasAborted) addFollowUps(state.shell.body, citations);

  /* persist the exchange + enable feedback once saved */
  if (!wasAborted) {
    persistAskPair(q, finalAnswer, citations, Number.isFinite(groundedness) ? groundedness : null)
      .then((assistantMsgId) => {
        if (assistantMsgId && foot.isConnected) attachFeedback(foot, assistantMsgId);
      })
      .catch((err) => console.warn("Could not persist conversation:", err));
  }

  setStreamingUI(false);
  input.focus();
  scrollThread(true);
}

/* ---------------------------------------------------------
   Stop streaming
   --------------------------------------------------------- */

stopBtn.addEventListener("click", () => {
  abortCtrl?.abort();
});

/* ---------------------------------------------------------
   Citation click → highlight evidence card
   --------------------------------------------------------- */

/* --- hover preview for [n] citation markers --- */

function showCiteTip(cite) {
  const n = cite.getAttribute("data-n");
  const c = (Array.isArray(lastCitations) ? lastCitations : []).find((x) => String(x.marker) === n);
  const tip = $("#citeTip");
  if (!c || !tip) return;
  const trail = Array.isArray(c.section_trail) ? c.section_trail.filter(Boolean).join(" › ") : "";
  const snippet = String(c.text || "").slice(0, 240);
  tip.innerHTML = `
    <div class="ct-head"><b>[${escapeHtml(n)}] ${escapeHtml(String(c.title || "Document"))}</b>${trail ? `<span>${escapeHtml(trail)}</span>` : ""}</div>
    <div class="ct-body">${escapeHtml(snippet)}${snippet.length === 240 ? "…" : ""}</div>`;
  tip.hidden = false;
  const r = cite.getBoundingClientRect();
  const tw = tip.offsetWidth;
  let left = r.left + r.width / 2 - tw / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
  let top = r.bottom + 8;
  if (top + tip.offsetHeight > window.innerHeight - 8) top = Math.max(8, r.top - tip.offsetHeight - 8);
  tip.style.left = left + "px";
  tip.style.top = top + "px";
}

function hideCiteTip() {
  const tip = $("#citeTip");
  if (tip) tip.hidden = true;
}

thread.addEventListener("mouseover", (e) => {
  const cite = e.target.closest(".cite");
  if (cite) showCiteTip(cite);
  else hideCiteTip();
});
thread.addEventListener("mouseout", () => hideCiteTip());
thread.addEventListener("click", (e) => {
  const cite = e.target.closest(".cite");
  if (!cite) return;
  hideCiteTip();
  highlightCitation(cite.getAttribute("data-n"));
});

thread.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const cite = e.target.closest(".cite");
  if (!cite) return;
  e.preventDefault();
  highlightCitation(cite.getAttribute("data-n"));
});

/* ---------------------------------------------------------
   Compare view (retrieval ablation, no LLM)
   --------------------------------------------------------- */

const COMPARE_COLS = [
  { key: "dense", label: "Dense · MiniLM", blurb: "semantic similarity only" },
  { key: "bm25", label: "BM25 · keyword", blurb: "exact terms only" },
  { key: "hybrid", label: "Hybrid · RRF", blurb: "dense + BM25 fused" },
  { key: "hybrid_rerank", label: "Hybrid + rerank", blurb: "cross-encoder rescored", best: true },
];

function showCompareIntro() {
  cmpIntro.hidden = false;
  cmpQbar.hidden = true;
  cmpGrid.innerHTML = "";
}

async function runCompare(query) {
  if (cmpBusy) return;
  cmpBusy = true;
  sendBtn.disabled = true;

  cmpIntro.hidden = true;
  cmpQbar.hidden = false;
  cmpQText.textContent = query;

  cmpGrid.innerHTML = COMPARE_COLS.map(
    (c) => `
    <div class="cmp-col">
      <div class="cmp-col-head"><span class="h4">${escapeHtml(c.label)}</span>${c.best ? '<span class="best-flag">best</span>' : ""}</div>
      <div class="cmp-col-body"><div class="cmp-none">running…</div></div>
    </div>`
  ).join("");

  try {
    const res = await authFetch("/api/search/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, k: 4 }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();

    COMPARE_COLS.forEach((col, ci) => {
      const results = Array.isArray(data[col.key]) ? data[col.key] : [];
      const colEl = cmpGrid.children[ci];
      colEl.classList.toggle("best", Boolean(col.best && results.length));
      const body = colEl.querySelector(".cmp-col-body");
      body.innerHTML = "";

      if (!results.length) {
        body.appendChild(el("div", "cmp-none", "No results"));
        return;
      }

      results.forEach((r, i) => {
        const title = escapeHtml(r.title || "Document");
        const trail = Array.isArray(r.section_trail)
          ? r.section_trail.filter(Boolean).map((x) => escapeHtml(x)).join(" › ")
          : "";
        const full = String(r.text || "");
        const snippet = full.length > 160 ? full.slice(0, 160) : full;
        const expandable = full.length > 160;
        const item = el(
          "div",
          "cmp-item",
          `
          <div><span class="rank">#${i + 1}</span><span class="t">${title}</span></div>
          ${trail ? `<div class="sec">${trail}</div>` : ""}
          ${full ? `<div class="sec snip">${escapeHtml(snippet)}${expandable ? "…" : ""}</div>` : ""}
          ${expandable ? `<button type="button" class="mini-btn xpnd" aria-expanded="false">Show full passage</button>` : ""}
          <div class="sc">score ${fmtScore(r.score)}</div>
          `
        );
        if (expandable) {
          const btn = item.querySelector(".xpnd");
          const snip = item.querySelector(".snip");
          btn.addEventListener("click", () => {
            const open = btn.getAttribute("aria-expanded") === "true";
            item.classList.toggle("open", !open);
            snip.textContent = open ? snippet + "…" : full;
            btn.setAttribute("aria-expanded", String(!open));
            btn.textContent = open ? "Show full passage" : "Collapse passage";
          });
        }
        body.appendChild(item);
      });
    });
  } catch (err) {
    console.error("Comparison failed:", err);
    cmpGrid.innerHTML = `<div class="cmp-col" style="grid-column:1/-1"><div class="cmp-col-body"><div class="cmp-none">Comparison failed — ${escapeHtml(err.message || "check the server")}</div></div></div>`;
  } finally {
    cmpBusy = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

/* ---------------------------------------------------------
   View switching (Ask ⇄ Compare)
   --------------------------------------------------------- */

function setView(v) {
  view = v;
  const asking = v === "ask";
  viewAsk.hidden = !asking;
  viewCompare.hidden = asking;
  const tabAsk = $("#tabAsk");
  const tabCompare = $("#tabCompare");
  tabAsk.classList.toggle("on", asking);
  tabCompare.classList.toggle("on", !asking);
  tabAsk.setAttribute("aria-pressed", asking ? "true" : "false");
  tabCompare.setAttribute("aria-pressed", asking ? "false" : "true");
  input.placeholder = asking ? "Ask about an uploaded document…" : "Type a query to compare retrieval modes (no LLM call)…";
  composerHint.textContent = asking ? "↵ send · shift+↵ newline" : "↵ run comparison";
  if (!asking) showCompareIntro();
  setTimeout(() => input.focus(), 50);
}

$("#tabAsk").addEventListener("click", () => setView("ask"));
$("#tabCompare").addEventListener("click", () => setView("compare"));
newChatBtn.addEventListener("click", () => newChat());

/* ---------------------------------------------------------
   Sidebar tabs (Chats ⇄ Library)
   --------------------------------------------------------- */

function setSideTab(tab) {
  const defs = [
    ["chats", "#sideTabChats", "#sideViewChats"],
    ["lib", "#sideTabLib", "#sideViewLib"],
    ["users", "#sideTabUsers", "#sideViewUsers"],
  ];
  defs.forEach(([key, tabSel, viewSel]) => {
    const tb = $(tabSel);
    const vw = $(viewSel);
    if (!tb || !vw) return;
    const on = tab === key;
    tb.classList.toggle("on", on);
    tb.setAttribute("aria-selected", on ? "true" : "false");
    vw.hidden = !on;
  });
  if (tab === "users" && currentUser && currentUser.role === "admin") void refreshUsers();
}

sideTabChats.addEventListener("click", () => setSideTab("chats"));
sideTabLib.addEventListener("click", () => setSideTab("lib"));
$("#sideTabUsers")?.addEventListener("click", () => setSideTab("users"));

/* ---------------------------------------------------------
   Responsive drawers
   --------------------------------------------------------- */

function closeDrawers() {
  libPanel.classList.remove("open");
  evPanel.classList.remove("open");
  backdrop.hidden = true;
}

$("#btnLib").addEventListener("click", () => {
  const willOpen = !libPanel.classList.contains("open");
  closeDrawers();
  backdrop.hidden = !willOpen;
  libPanel.classList.toggle("open", willOpen);
  if (willOpen) setSideTab("lib");
});

$("#btnEv").addEventListener("click", () => {
  const willOpen = !evPanel.classList.contains("open");
  closeDrawers();
  backdrop.hidden = !willOpen;
  evPanel.classList.toggle("open", willOpen);
});

backdrop.addEventListener("click", closeDrawers);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDrawers();
});

/* ---------------------------------------------------------
   Composer behaviour
   --------------------------------------------------------- */

function autoGrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
}
input.addEventListener("input", autoGrow);

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void ask();
  }
});
sendBtn.addEventListener("click", () => void ask());

/* suggestions on the empty state */
$$("#suggestions button").forEach((b) => {
  b.addEventListener("click", () => {
    input.value = b.getAttribute("data-q");
    autoGrow();
    input.focus();
  });
});

/* keyboard: "/" focuses the composer */
document.addEventListener("keydown", (e) => {
  if (e.key !== "/") return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if ($("#modalRoot").childElementCount) return;
  if (view !== "ask") setView("ask");
  e.preventDefault();
  input.focus();
});

/* ---------------------------------------------------------
   Init
   --------------------------------------------------------- */

async function bootstrap() {
  hydrateIcons(document);
  setDropState(null, DROP_IDLE.b, DROP_IDLE.s);
  showCompareIntro();
  setStreamingUI(false);

  if (!window.marked) console.warn("marked.js did not load — markdown will render as plain text.");
  if (!window.DOMPurify) console.warn("DOMPurify did not load — answers will render as plain text (sanitizer unavailable).");

  document.body.classList.remove("is-admin");
  if (token) {
    try {
      const res = await authFetch("/api/auth/me", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        await enterApp(data.user);
        return;
      }
    } catch (e) { /* fall through to the login screen */ }
    token = "";
    localStorage.removeItem("eka_token");
  }
  showLogin();
}

bootstrap();
