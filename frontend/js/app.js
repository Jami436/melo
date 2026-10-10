// App bootstrap — page rendering, search, library and likes.
// Consumes the placeholder catalog from api.js.

const ICONS = {
  play: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 5.6v12.8L19 12z"/></svg>',
  heart:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21.2l7.8-7.8 1.1-1.1a5.5 5.5 0 0 0 0-7.7z"/></svg>',
  user:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12.5a4.25 4.25 0 1 0 0-8.5 4.25 4.25 0 0 0 0 8.5zM4.5 20a7.5 7.5 0 0 1 15 0z"/></svg>',
  logout:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H15M11 16l-4-4 4-4M7 12h9"/></svg>',
};

const likedIds = new Set(
  PLACEHOLDER_TRACKS.filter((t) => t.liked).map((t) => t.id)
);

/* ---------- helpers ---------- */

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function formatDuration(seconds) {
  if (!isFinite(seconds) || seconds < 0) seconds = 0;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function trackById(id) {
  return PLACEHOLDER_TRACKS.find((t) => t.id === id) || null;
}

/* ---------- markup ---------- */

function trackCard(track) {
  return `<article class="card">
      <div class="card-cover">
        ${coverSvg(track.cover)}
        <button type="button" class="card-play" data-play="track" data-id="${track.id}"
          aria-label="Play ${escapeHtml(track.title)} by ${escapeHtml(track.artist)}">${ICONS.play}</button>
      </div>
      <h3 class="card-title">${escapeHtml(track.title)}</h3>
      <p class="card-sub">${escapeHtml(track.artist)}</p>
    </article>`;
}

function playlistCard(playlist) {
  return `<article class="card">
      <div class="card-cover">
        ${coverSvg(playlist.cover)}
        <button type="button" class="card-play" data-play="playlist" data-id="${playlist.id}"
          aria-label="Play ${escapeHtml(playlist.title)}">${ICONS.play}</button>
      </div>
      <h3 class="card-title">${escapeHtml(playlist.title)}</h3>
      <p class="card-sub">${playlist.songs} songs</p>
    </article>`;
}

function trackRow(track) {
  const liked = likedIds.has(track.id);
  return `<li class="track-row">
      <button type="button" class="track-main" data-play="track" data-id="${track.id}"
        aria-label="Play ${escapeHtml(track.title)} by ${escapeHtml(track.artist)}">
        <span class="track-cover">${coverSvg(track.cover)}</span>
        <span class="track-info">
          <span class="track-title">${escapeHtml(track.title)}</span>
          <span class="track-artist">${escapeHtml(track.artist)}</span>
        </span>
        <span class="track-dur">${formatDuration(track.duration)}</span>
      </button>
      <button type="button" class="icon-btn heart-btn" data-like="${track.id}"
        aria-label="${liked ? "Remove from" : "Save to"} Liked Songs" aria-pressed="${liked}">${ICONS.heart}</button>
    </li>`;
}

function cardSkeletons(count) {
  let out = "";
  for (let i = 0; i < count; i++) {
    out += `<article class="card" aria-hidden="true">
        <div class="skeleton sk-cover"></div>
        <div class="skeleton sk-line" style="width:72%"></div>
        <div class="skeleton sk-line" style="width:44%"></div>
      </article>`;
  }
  return out;
}

function rowSkeletons(count) {
  let out = "";
  for (let i = 0; i < count; i++) {
    out += `<li class="track-row sk-row" aria-hidden="true">
        <div class="skeleton sk-thumb"></div>
        <div class="sk-lines">
          <div class="skeleton sk-line" style="width:48%;margin-top:0"></div>
          <div class="skeleton sk-line" style="width:28%"></div>
        </div>
        <div class="skeleton sk-line sk-dur" style="margin-top:0"></div>
      </li>`;
  }
  return out;
}

/* ---------- home ---------- */

function setGreeting() {
  const now = new Date();
  const hour = now.getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  const greetingEl = document.getElementById("greeting");
  if (greetingEl) greetingEl.textContent = greeting;

  const label = document.getElementById("today-label");
  if (label) {
    label.textContent = now.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
  }
}

async function initHome() {
  const row = document.getElementById("recent-row");
  const grid = document.getElementById("made-grid");
  if (!row && !grid) return;

  setGreeting();

  if (row) row.innerHTML = cardSkeletons(5);
  if (grid) grid.innerHTML = cardSkeletons(6);

  const { tracks, playlists } = await fetchCatalog();

  if (row) {
    row.innerHTML = tracks.filter((t) => t.recent).map(trackCard).join("");
    row.setAttribute("aria-busy", "false");
  }
  if (grid) {
    grid.innerHTML = playlists.map(playlistCard).join("");
    grid.setAttribute("aria-busy", "false");
  }
}

/* ---------- search ---------- */

function initSearch() {
  const input = document.getElementById("search-input");
  if (!input) return;

  const results = document.getElementById("search-results");
  const empty = document.getElementById("search-empty");
  const label = document.getElementById("results-label");
  const clear = document.getElementById("search-clear");
  const status = document.getElementById("search-status");
  let timer = null;

  function reset() {
    results.innerHTML = "";
    results.setAttribute("aria-busy", "false");
    label.hidden = true;
    empty.hidden = false;
    empty.innerHTML =
      "<strong>Nothing here yet.</strong><p>Search for something you love.</p>";
    status.textContent = "";
  }

  function renderResults(hits, query) {
    results.setAttribute("aria-busy", "false");
    if (!hits.length) {
      results.innerHTML = "";
      label.hidden = true;
      empty.hidden = false;
      empty.innerHTML =
        `<strong>No matches for “${escapeHtml(query)}”.</strong>` +
        "<p>Try another artist, or a shorter search.</p>";
      status.textContent = `No results for ${query}`;
      return;
    }
    empty.hidden = true;
    label.hidden = false;
    label.textContent = `${hits.length} result${hits.length > 1 ? "s" : ""}`;
    results.innerHTML = hits.map(trackRow).join("");
    status.textContent = `${hits.length} results`;
  }

  input.addEventListener("input", () => {
    const query = input.value.trim();
    clearTimeout(timer);
    clear.hidden = input.value.length === 0;

    if (!query) {
      reset();
      return;
    }

    empty.hidden = true;
    label.hidden = true;
    results.setAttribute("aria-busy", "true");
    results.innerHTML = rowSkeletons(4);

    timer = setTimeout(async () => {
      const hits = await searchTracks(query);
      renderResults(hits, query);
    }, 180);
  });

  clear.addEventListener("click", () => {
    input.value = "";
    clear.hidden = true;
    input.focus();
    reset();
  });

  reset();
}

/* ---------- library ---------- */

function renderLiked() {
  const panel = document.getElementById("panel-liked");
  if (!panel) return;
  const liked = PLACEHOLDER_TRACKS.filter((t) => likedIds.has(t.id));
  if (!liked.length) {
    panel.innerHTML =
      '<div class="empty-state"><strong>No liked songs yet.</strong>' +
      "<p>Tap the heart on any track to save it here.</p></div>";
    return;
  }
  panel.innerHTML = `<ul class="track-list">${liked.map(trackRow).join("")}</ul>`;
}

function initLibrary() {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  if (!tabs.length) return;

  const panelPlaylists = document.getElementById("panel-playlists");
  const panelLiked = document.getElementById("panel-liked");

  panelPlaylists.innerHTML = cardSkeletons(4);

  async function loadPlaylists() {
    const { playlists } = await fetchLibrary();
    panelPlaylists.setAttribute("aria-busy", "false");
    if (!playlists.length) {
      panelPlaylists.innerHTML =
        '<div class="empty-state"><strong>No playlists yet.</strong>' +
        "<p>Made-for-you mixes will land here.</p></div>";
      return;
    }
    panelPlaylists.innerHTML = `<div class="card-grid">${playlists
      .map(playlistCard)
      .join("")}</div>`;
  }

  function selectTab(tab) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    const target = tab.getAttribute("aria-controls");
    panelPlaylists.hidden = target !== "panel-playlists";
    panelLiked.hidden = target !== "panel-liked";
    if (target === "panel-liked") renderLiked();
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      event.preventDefault();
      const dir = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(i + dir + tabs.length) % tabs.length];
      next.focus();
      selectTab(next);
    });
  });

  loadPlaylists();
}

/* ---------- likes ---------- */

function syncLikeButtons(id) {
  const on = likedIds.has(id);
  document.querySelectorAll(`[data-like="${id}"]`).forEach((btn) => {
    btn.setAttribute("aria-pressed", String(on));
    btn.classList.toggle("is-liked", on);
    if (btn.id !== "like-btn") {
      btn.setAttribute(
        "aria-label",
        on ? "Remove from Liked Songs" : "Save to Liked Songs"
      );
    }
  });
}

function toggleLike(id) {
  if (!id) return;
  if (likedIds.has(id)) {
    likedIds.delete(id);
  } else {
    likedIds.add(id);
  }
  syncLikeButtons(id);

  const likedPanel = document.getElementById("panel-liked");
  if (likedPanel && !likedPanel.hidden) renderLiked();
}

/* ---------- playback wiring ---------- */

function handlePlay(kind, id) {
  if (typeof loadTrack !== "function") return;

  if (kind === "track") {
    const track = trackById(id);
    if (track) loadTrack(track, PLACEHOLDER_TRACKS);
    return;
  }

  if (kind === "playlist") {
    const playlist = PLACEHOLDER_PLAYLISTS.find((p) => p.id === id);
    if (!playlist) return;
    const queue = playlist.tracks.map(trackById).filter(Boolean);
    if (queue.length) loadTrack(queue[0], queue);
  }
}

document.addEventListener("click", (event) => {
  const playEl = event.target.closest("[data-play]");
  if (playEl) {
    handlePlay(playEl.dataset.play, playEl.dataset.id);
    return;
  }

  const likeEl = event.target.closest("[data-like]");
  if (likeEl) toggleLike(likeEl.dataset.like);
});

document.addEventListener("melo:track", (event) => {
  const track = event.detail;
  const likeBtn = document.getElementById("like-btn");
  if (!likeBtn) return;
  likeBtn.dataset.like = track.id;
  const on = likedIds.has(track.id);
  likeBtn.classList.toggle("is-liked", on);
  likeBtn.setAttribute("aria-pressed", String(on));
  likeBtn.setAttribute(
    "aria-label",
    on ? "Remove from Liked Songs" : "Save to Liked Songs"
  );
});

// "/" focuses search when available.
document.addEventListener("keydown", (event) => {
  if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
  const el = event.target;
  const tag = el && el.tagName ? el.tagName.toLowerCase() : "";
  if (tag === "input" || tag === "textarea" || (el && el.isContentEditable)) return;
  const input = document.getElementById("search-input");
  if (input) {
    event.preventDefault();
    input.focus();
  }
});

/* ---------- account (sidebar) ---------- */

async function initAccount() {
  const slot = document.getElementById("account-slot");
  if (!slot) return; // no sidebar on this page (e.g. the auth page)

  const sidebar = document.getElementById("sidebar");
  const authHref = (sidebar && sidebar.dataset.authHref) || "pages/auth.html";

  if (!getToken()) {
    slot.innerHTML = `<a class="account-btn" href="${authHref}">${ICONS.user}<span>Log in</span></a>`;
    return;
  }

  try {
    const user = await authApi.me();
    renderAccountUser(slot, user, authHref);
  } catch {
    // Token missing/expired/invalid — drop it and show the signed-out state.
    clearToken();
    slot.innerHTML = `<a class="account-btn" href="${authHref}">${ICONS.user}<span>Log in</span></a>`;
  }
}

function renderAccountUser(slot, user, authHref) {
  const name = user.username || user.email || "You";
  const initial = escapeHtml(name.trim().charAt(0).toUpperCase() || "?");
  slot.innerHTML =
    `<div class="account-user"><span class="account-avatar" aria-hidden="true">${initial}</span>` +
      `<span class="account-name">${escapeHtml(name)}</span></div>` +
    `<button type="button" class="account-btn" id="logout-btn">${ICONS.logout}<span>Log out</span></button>`;

  const logout = document.getElementById("logout-btn");
  if (logout) {
    logout.addEventListener("click", () => {
      authApi.logout();
      window.location.href = authHref;
    });
  }
}

/* ---------- auth page ---------- */

function initAuthPage() {
  const loginForm = document.getElementById("login-form");
  const signupForm = document.getElementById("signup-form");
  if (!loginForm && !signupForm) return; // not on the auth page

  const message = document.getElementById("auth-message");
  const logo = document.querySelector(".auth-logo");
  const homeHref = (logo && logo.getAttribute("href")) || "../index.html";

  const tabs = Array.from(document.querySelectorAll(".auth-tabs [role='tab']"));
  const panels = { login: document.getElementById("panel-login"), signup: document.getElementById("panel-signup") };

  function showMessage(text, isError = false) {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("is-error", isError);
  }

  function selectTab(tab) {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    Object.entries(panels).forEach(([key, panel]) => {
      if (panel) panel.hidden = key !== tab.dataset.panel;
    });
    showMessage("");
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      next.focus();
      selectTab(next);
    });
  });

  async function withPending(form, pendingText, run) {
    const submit = form.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;
    showMessage(pendingText);
    try {
      await run();
    } catch (err) {
      showMessage(err.message || "Something went wrong.", true);
    } finally {
      if (submit) submit.disabled = false;
    }
  }

  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = new FormData(loginForm);
      withPending(loginForm, "Logging in…", async () => {
        await authApi.login(String(data.get("email") || "").trim(), String(data.get("password") || ""));
        window.location.href = homeHref;
      });
    });
  }

  if (signupForm) {
    signupForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = new FormData(signupForm);
      const email = String(data.get("email") || "").trim();
      const password = String(data.get("password") || "");
      withPending(signupForm, "Creating your account…", async () => {
        await authApi.signup({ email, username: String(data.get("username") || "").trim(), password });
        await authApi.login(email, password); // log straight in after signup
        window.location.href = homeHref;
      });
    });
  }
}

/* ---------- boot ---------- */

document.addEventListener("DOMContentLoaded", () => {
  initHome();
  initSearch();
  initLibrary();
  initAccount();
  initAuthPage();
});
