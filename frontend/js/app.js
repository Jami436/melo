// App bootstrap — page rendering, search, library, uploads and likes.
// Consumes the live catalog from api.js.

const ICONS = {
  play: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 5.6v12.8L19 12z"/></svg>',
  heart:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21.2l7.8-7.8 1.1-1.1a5.5 5.5 0 0 0 0-7.7z"/></svg>',
  user:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12.5a4.25 4.25 0 1 0 0-8.5 4.25 4.25 0 0 0 0 8.5zM4.5 20a7.5 7.5 0 0 1 15 0z"/></svg>',
  logout:
    '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H15M11 16l-4-4 4-4M7 12h9"/></svg>',
};

const likedIds = new Set();

/* ---------- helpers ---------- */

function isPagesDir() {
  return /(^|\/)pages\//.test(window.location.pathname);
}

function loginHref() {
  return isPagesDir() ? "login.html" : "pages/login.html";
}

function indexHref() {
  return isPagesDir() ? "../index.html" : "index.html";
}

function stateMarkup(title, text, retry = false) {
  return `<div class="empty-state">
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(text)}</p>
      ${retry ? '<button type="button" class="btn-state" data-retry>Try again</button>' : ""}
    </div>`;
}

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
  return catalogTracks.find((t) => t.id === id) || null;
}

function coverImage(track) {
  if (track && track.coverUrl) {
    return `<img src="${escapeHtml(track.coverUrl)}" class="cover-art" alt="Cover" loading="lazy" />`;
  }
  return coverSvg(track && track.cover !== undefined ? track.cover : 0);
}

/* ---------- markup ---------- */

function trackCard(track) {
  return `<article class="card" data-play="track" data-id="${track.id}" tabindex="0"
      role="button" aria-label="Play ${escapeHtml(track.title)} by ${escapeHtml(track.artist)}">
      <div class="card-cover">
        ${coverImage(track)}
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
        ${coverImage(playlist)}
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
        <span class="track-cover">${coverImage(track)}</span>
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

  if (row) {
    row.innerHTML = cardSkeletons(5);
    row.setAttribute("aria-busy", "true");
  }
  if (grid) {
    grid.innerHTML = cardSkeletons(6);
    grid.setAttribute("aria-busy", "true");
  }

  try {
    const { tracks, playlists } = await fetchCatalog();

    if (row) {
      row.classList.toggle("is-state", tracks.length === 0);
      row.innerHTML = tracks.length
        ? tracks.map(trackCard).join("")
        : stateMarkup(
            "Your library is empty.",
            "Upload a track to start listening.",
            false
          );
      row.setAttribute("aria-busy", "false");
    }

    if (grid) {
      grid.innerHTML = playlists.length
        ? playlists.map(playlistCard).join("")
        : stateMarkup(
            "No playlists yet.",
            "Create one from your library.",
            false
          );
      grid.setAttribute("aria-busy", "false");
    }
  } catch (err) {
    const message = err.message || "Something went wrong while loading your music.";
    if (row) {
      row.classList.add("is-state");
      row.innerHTML = stateMarkup("Couldn't load your music.", message, true);
      row.setAttribute("aria-busy", "false");
    }
    if (grid) {
      grid.innerHTML = stateMarkup("Couldn't load your music.", message, true);
      grid.setAttribute("aria-busy", "false");
    }

    [row, grid].filter(Boolean).forEach((container) => {
      container.querySelectorAll("[data-retry]").forEach((btn) => {
        btn.addEventListener("click", initHome);
      });
    });
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
      try {
        const hits = await searchTracks(query);
        renderResults(hits, query);
      } catch (err) {
        results.innerHTML = "";
        results.setAttribute("aria-busy", "false");
        label.hidden = true;
        empty.hidden = false;
        empty.innerHTML = stateMarkup(
          "Couldn't search right now.",
          err.message || "Check the connection and try again."
        );
        status.textContent = "Search failed";
      }
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
  const liked = catalogTracks.filter((t) => likedIds.has(t.id));
  if (!liked.length) {
    panel.innerHTML =
      '<div class="empty-state"><strong>No liked songs yet.</strong>' +
      "<p>Tap the heart on any track to save it here.</p></div>";
    return;
  }
  panel.innerHTML = `<ul class="track-list">${liked.map(trackRow).join("")}</ul>`;
}

function renderPlaylists(playlists) {
  const content =
    document.getElementById("playlists-content") ||
    document.getElementById("panel-playlists");
  if (!content) return;
  content.setAttribute("aria-busy", "false");
  if (!playlists.length) {
    content.innerHTML =
      '<div class="empty-state"><strong>No playlists yet.</strong>' +
      "<p>Create your first playlist above.</p></div>";
    return;
  }
  content.innerHTML = `<div class="card-grid">${playlists
    .map(playlistCard)
    .join("")}</div>`;
}

function initLibrary() {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  if (!tabs.length) return;

  const panelPlaylists = document.getElementById("panel-playlists");
  const panelLiked = document.getElementById("panel-liked");
  const playlistContent =
    document.getElementById("playlists-content") || panelPlaylists;

  playlistContent.innerHTML = cardSkeletons(4);
  playlistContent.setAttribute("aria-busy", "true");

  async function loadPlaylists() {
    try {
      const { playlists } = await fetchLibrary();
      renderPlaylists(playlists);
    } catch (err) {
      playlistContent.innerHTML = stateMarkup(
        "Couldn't load your playlists.",
        err.message || "Check the connection and try again."
      );
      playlistContent.setAttribute("aria-busy", "false");
    }
  }

  document.addEventListener("melo:playlists", loadPlaylists);

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

function initCreatePlaylist() {
  const btn = document.getElementById("create-playlist-btn");
  const dialog = document.getElementById("create-playlist-dialog");
  const form = document.getElementById("create-playlist-form");
  const cancel = document.getElementById("cancel-create-playlist");
  const message = document.getElementById("create-playlist-message");
  if (!btn || !dialog || !form) return;

  function showMessage(text, isError = false) {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("is-error", isError);
  }

  btn.addEventListener("click", () => {
    showMessage("");
    form.reset();
    dialog.showModal();
  });

  cancel.addEventListener("click", () => {
    dialog.close();
    showMessage("");
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const name = String(data.get("name") || "").trim();
    const isPublic = data.get("is_public") === "on";
    if (!name) {
      showMessage("Please enter a playlist name.", true);
      return;
    }
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    showMessage("Creating playlist…");
    try {
      await playlistsApi.create(name, isPublic);
      dialog.close();
      showMessage("");
      document.dispatchEvent(new CustomEvent("melo:playlists"));
    } catch (err) {
      showMessage(err.message || "Failed to create playlist.", true);
    } finally {
      submit.disabled = false;
    }
  });
}

/* ---------- upload ---------- */

function initUploadForm() {
  const form = document.getElementById("upload-form");
  if (!form) return;

  const message = document.getElementById("upload-message");
  const submit = form.querySelector('button[type="submit"]');

  function showMessage(text, isError = false) {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("is-error", isError);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = new FormData(form);
    const title = String(data.get("title") || "").trim();
    const artist = String(data.get("artist") || "").trim();
    const file = data.get("file");

    if (!title || !artist) {
      showMessage("Please add a title and artist.", true);
      return;
    }
    if (!file || !file.name) {
      showMessage("Please choose an audio file.", true);
      return;
    }

    if (submit) submit.disabled = true;
    showMessage("Uploading…");

    try {
      const track = await uploadTrack({ title, artist, file });
      form.reset();
      showMessage(`Uploaded “${track.title}”. It's now on Home.`);
      await fetchTracks().catch(() => {});
    } catch (err) {
      showMessage(err.message || "Upload failed. Please try again.", true);
    } finally {
      if (submit) submit.disabled = false;
    }
  });
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
    const source = trackById(id);
    if (!source) return;
    const withStreams = catalogTracks.map((t) => ({
      ...t,
      src: getStreamUrl(t.id),
    }));
    const track = withStreams.find((t) => t.id === id) || {
      ...source,
      src: getStreamUrl(source.id),
    };
    loadTrack(track, withStreams);
    return;
  }

  if (kind === "playlist") {
    // No playlist backend yet; nothing to play.
    return;
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

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest('[data-play][role="button"]');
  if (!card) return;
  event.preventDefault();
  handlePlay(card.dataset.play, card.dataset.id);
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
  const authHref = (sidebar && sidebar.dataset.authHref) || loginHref();

  if (!getToken()) {
    slot.innerHTML = `<a class="account-btn" href="${authHref}">${ICONS.user}<span>Log in</span></a>`;
    return;
  }

  try {
    const user = await authApi.me();
    renderAccountUser(slot, user, authHref);
  } catch (err) {
    // Token missing/expired/invalid — send the user back to login.
    clearToken();
    if (err.status === 401) {
      window.location.replace(authHref);
      return;
    }
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

async function initAuthPage() {
  const loginForm = document.getElementById("login-form");
  const signupForm = document.getElementById("signup-form");
  if (!loginForm && !signupForm) return; // not on an auth page

  const message = document.getElementById("auth-message");
  const homeHref = indexHref();

  // Already signed in? Go straight to the app.
  if (getToken()) {
    try {
      await getMe();
      window.location.replace(homeHref);
      return;
    } catch (err) {
      if (err.status === 401) clearToken();
    }
  }

  function showMessage(text, isError = false) {
    if (!message) return;
    message.textContent = text;
    message.classList.toggle("is-error", isError);
  }

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
    loginForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(loginForm);
      withPending(loginForm, "Logging in…", async () => {
        await login(
          String(data.get("email") || "").trim(),
          String(data.get("password") || "")
        );
        window.location.href = homeHref;
      });
    });
  }

  if (signupForm) {
    signupForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(signupForm);
      const email = String(data.get("email") || "").trim();
      const password = String(data.get("password") || "");
      withPending(signupForm, "Creating your account…", async () => {
        await signup({
          email,
          username: String(data.get("username") || "").trim(),
          password,
        });
        await login(email, password); // log straight in after signup
        window.location.href = homeHref;
      });
    });
  }
}

/* ---------- boot ---------- */

document.addEventListener("DOMContentLoaded", () => {
  // Any page with the sidebar requires a session.
  const protectedPage = Boolean(document.getElementById("account-slot"));
  if (protectedPage && !getToken()) {
    window.location.replace(loginHref());
    return;
  }

  initHome();
  initSearch();
  initLibrary();
  initCreatePlaylist();
  initUploadForm();
  initAccount();
  initAuthPage();
});
