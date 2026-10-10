// Central place for all calls to the Melo FastAPI backend.
//
// Auth endpoints (/auth/*) are live. The catalog (tracks/search/library) is
// still served from placeholder data at the bottom of this file until those
// endpoints exist — see the note above that section.

const API_BASE_URL = "http://localhost:8000";
const TOKEN_KEY = "melo_token";

// ---- token storage -------------------------------------------------------
// localStorage keeps the session across page loads. It is readable by any
// script on the page; if that ever becomes a concern, switch to an httpOnly
// cookie issued by the backend.

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ---- request helper ------------------------------------------------------

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers["Content-Type"] = "application/json";

  // Attach the bearer token automatically when we have one.
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    // fetch only rejects on network/CORS failures.
    throw new Error("Can't reach the server. Is the backend running?");
  }

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const data = isJson ? await res.json() : null;

  if (!res.ok) {
    const error = new Error(formatErrorDetail(data, res.status));
    error.status = res.status;
    throw error;
  }

  return data;
}

// FastAPI returns `detail` as a string for our own errors, or as a list for
// validation (422) errors. Normalise both into a readable message.
function formatErrorDetail(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || "Invalid input").join(", ");
  }
  return `Request failed (${status})`;
}

// ---- auth API ------------------------------------------------------------

const authApi = {
  signup(payload) {
    return apiRequest("/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async login(email, password) {
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },

  me() {
    return apiRequest("/auth/me");
  },

  logout() {
    clearToken();
  },
};

/* ============================================================
   Placeholder catalog
   Swap fetchCatalog / searchTracks / fetchLibrary for the
   real apiRequest(...) calls when the endpoints exist.
   ============================================================ */

/* Cover placeholders are drawn from the palette only: a lifted
   black or cream field with cream/black line art. No images. */
const COVER_ART = [
  '<circle cx="50" cy="50" r="32"/><circle cx="50" cy="50" r="20"/><circle cx="50" cy="50" r="8"/>',
  '<path d="M-10 40 40-10"/><path d="M-10 70 70-10"/><path d="M0 100 100 0"/><path d="M30 110 110 30"/><path d="M60 110 110 60"/>',
  '<path d="M14 86a72 72 0 0 1 72-72"/><path d="M14 62a48 48 0 0 1 48-48"/><path d="M14 38a24 24 0 0 1 24-24"/>',
  '<g fill="__INK__" stroke="none"><circle cx="26" cy="26" r="4"/><circle cx="50" cy="26" r="4"/><circle cx="74" cy="26" r="4"/><circle cx="26" cy="50" r="4"/><circle cx="50" cy="50" r="4"/><circle cx="74" cy="50" r="4"/><circle cx="26" cy="74" r="4"/><circle cx="50" cy="74" r="4"/><circle cx="74" cy="74" r="4"/></g>',
  '<path d="M50 16 84 78H16z"/><circle cx="50" cy="58" r="9"/>',
  '<path d="M12 40q19-18 38 0t38 0"/><path d="M12 60q19-18 38 0t38 0"/><path d="M12 80q19-18 38 0t38 0"/>',
  '<path d="M20 80V52"/><path d="M36 80V34"/><path d="M52 80V60"/><path d="M68 80V24"/><path d="M84 80V44"/>',
  '<circle cx="50" cy="50" r="30"/><path d="M14 50h72"/>',
  '<path d="M50 14 86 50 50 86 14 50z"/><path d="M50 32 68 50 50 68 32 50z"/>',
  '<g fill="__INK__" stroke="none"><rect x="18" y="18" width="28" height="28" rx="6"/><rect x="54" y="18" width="28" height="28" rx="14"/><rect x="18" y="54" width="28" height="28" rx="14"/><rect x="54" y="54" width="28" height="28" rx="6"/></g>',
  '<path d="M44 20v60"/><path d="M56 20v60"/><path d="M20 50h60"/>',
];

// Returns inline SVG markup for a placeholder cover.
function coverSvg(index) {
  const n = ((Math.abs(index) % COVER_ART.length) + COVER_ART.length) % COVER_ART.length;
  const inverted = n % 3 === 2;
  const bg = inverted ? "#F5EDE0" : "#141414";
  const ink = inverted ? "#0A0A0A" : "#F5EDE0";
  const art = COVER_ART[n].replace(/__INK__/g, ink);
  return (
    '<svg class="cover-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false">' +
    `<rect width="100" height="100" fill="${bg}"/>` +
    `<g fill="none" stroke="${ink}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="${inverted ? 0.85 : 0.7}">${art}</g>` +
    "</svg>"
  );
}

// src is intentionally empty until the backend serves audio files.
const PLACEHOLDER_TRACKS = [
  { id: "t1", title: "Slow Tide", artist: "Nomi Kalu", duration: 222, cover: 0, recent: true, liked: true, src: "" },
  { id: "t2", title: "Paper Streets", artist: "Vela Rue", duration: 245, cover: 1, recent: true, src: "" },
  { id: "t3", title: "Quiet Motion", artist: "Juniper Fields", duration: 207, cover: 2, recent: true, liked: true, src: "" },
  { id: "t4", title: "Held Together", artist: "Marlow Bain", duration: 174, cover: 3, src: "" },
  { id: "t5", title: "Evening Radio", artist: "Cedar House", duration: 247, cover: 4, recent: true, liked: true, src: "" },
  { id: "t6", title: "Small Hours", artist: "Ilo Bennett", duration: 258, cover: 5, src: "" },
  { id: "t7", title: "Runaway Light", artist: "Sable Nine", duration: 191, cover: 6, src: "" },
  { id: "t8", title: "Open Window", artist: "Fennel Coast", duration: 229, cover: 7, recent: true, liked: true, src: "" },
  { id: "t9", title: "Soft Landing", artist: "Aria Voss", duration: 167, cover: 8, src: "" },
  { id: "t10", title: "First Light", artist: "Kestrel Row", duration: 216, cover: 9, liked: true, src: "" },
  { id: "t11", title: "Midnight Cinema", artist: "Theo Lane", duration: 284, cover: 10, recent: true, src: "" },
  { id: "t12", title: "Paper Moon", artist: "Wren Halloway", duration: 183, cover: 0, src: "" },
];

const PLACEHOLDER_PLAYLISTS = [
  { id: "p1", title: "Late Night Drive", songs: 24, cover: 1, inLibrary: true, tracks: ["t1", "t11", "t7", "t2"] },
  { id: "p2", title: "Slow Mornings", songs: 18, cover: 5, inLibrary: true, tracks: ["t10", "t6", "t12"] },
  { id: "p3", title: "Deep Focus", songs: 32, cover: 3, tracks: ["t3", "t4", "t9"] },
  { id: "p4", title: "Weekend Reset", songs: 21, cover: 7, inLibrary: true, tracks: ["t8", "t7", "t5"] },
  { id: "p5", title: "Quiet Commute", songs: 27, cover: 2, tracks: ["t6", "t12", "t3"] },
  { id: "p6", title: "After Hours", songs: 16, cover: 10, inLibrary: true, tracks: ["t11", "t1", "t9"] },
];

const LATENCY = { catalog: 520, search: 380, library: 460 };

function delay(ms, value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// Placeholder replacement for apiRequest("/catalog")
function fetchCatalog() {
  return delay(LATENCY.catalog, {
    tracks: PLACEHOLDER_TRACKS,
    playlists: PLACEHOLDER_PLAYLISTS,
  });
}

// Placeholder replacement for apiRequest("/search?q=...")
function searchTracks(query) {
  const q = String(query || "").trim().toLowerCase();
  const hits = !q
    ? []
    : PLACEHOLDER_TRACKS.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          t.artist.toLowerCase().includes(q)
      );
  return delay(LATENCY.search, hits);
}

// Placeholder replacement for apiRequest("/library")
function fetchLibrary() {
  return delay(LATENCY.library, {
    playlists: PLACEHOLDER_PLAYLISTS.filter((p) => p.inLibrary),
  });
}
