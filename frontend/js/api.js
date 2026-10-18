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

const playlistsApi = {
  list() {
    return apiRequest("/playlists");
  },

  create(name, isPublic = true) {
    return apiRequest("/playlists", {
      method: "POST",
      body: JSON.stringify({ name, is_public: isPublic }),
    });
  },
};

/* ============================================================
   Real catalog (backed by /tracks).
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

// Tracks fetched from /tracks, each with a src pointing at the stream endpoint.
let catalogTracks = [];

async function fetchTracks() {
  const { items } = await apiRequest("/tracks?page=1&size=100");
  catalogTracks = items.map((t) => ({
    id: String(t.id),
    title: t.title,
    artist: t.artist,
    album: t.album ?? null,
    duration: t.duration_seconds || 0,
    cover: 0,
    coverUrl: t.cover_path
      ? `${API_BASE_URL}/covers/${t.cover_path}`
      : null,
    src: `${API_BASE_URL}/tracks/${t.id}/stream`,
    recent: true,
    liked: false,
  }));
  return catalogTracks;
}

// Replaces the old placeholder catalog.
function fetchCatalog() {
  return fetchTracks().then((tracks) => ({ tracks, playlists: [] }));
}

// Client-side search over the fetched catalog (no search endpoint yet).
function searchTracks(query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return Promise.resolve([]);
  const hits = catalogTracks.filter(
    (t) => t.title.toLowerCase().includes(q) || t.artist.toLowerCase().includes(q)
  );
  return Promise.resolve(hits);
}

// No playlists backend yet, so the library starts empty.
function fetchLibrary() {
  return playlistsApi.list().then((playlists) => ({ playlists }));
}
