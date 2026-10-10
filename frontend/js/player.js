// Handles the bottom audio player bar.
// Keeps the original element IDs (audio-player, play-pause-btn,
// now-playing, prev-btn, next-btn) so playback wiring stays intact.

const audio = document.getElementById("audio-player");
const playPauseBtn = document.getElementById("play-pause-btn");
const nowPlaying = document.getElementById("now-playing");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");

const npTitle = document.getElementById("np-title");
const npArtist = document.getElementById("np-artist");
const npCover = document.getElementById("np-cover");
const progressBar = document.getElementById("progress-bar");
const progressFill = document.getElementById("progress-fill");
const currentTimeEl = document.getElementById("current-time");
const durationEl = document.getElementById("duration");
const volumeSlider = document.getElementById("volume-slider");
const volumeFill = document.getElementById("volume-fill");
const shuffleBtn = document.getElementById("shuffle-btn");
const repeatBtn = document.getElementById("repeat-btn");

const SIM_STEP = 0.25;

let isPlaying = false;
let queue = [];
let index = -1;
let shuffle = false;
let repeat = false;
let simTimer = null;
let simTime = 0;

function currentTrack() {
  return queue[index] || null;
}

function hasSource(track) {
  return Boolean(track && track.src);
}

function formatTime(seconds) {
  if (!isFinite(seconds) || seconds < 0) seconds = 0;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function setFill(el, percent) {
  if (el) el.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

function updateProgress(current, total) {
  const percent = total ? (current / total) * 100 : 0;
  progressBar.value = percent;
  setFill(progressFill, percent);
  currentTimeEl.textContent = formatTime(current);
  durationEl.textContent = formatTime(total);
  progressBar.setAttribute(
    "aria-valuetext",
    `${formatTime(current)} of ${formatTime(total)}`
  );
}

function renderNowPlaying(track) {
  if (!track) {
    npTitle.textContent = "No track playing";
    npArtist.textContent = "Pick something you love";
    npCover.innerHTML = "";
    updateProgress(0, 0);
    return;
  }
  npTitle.textContent = track.title;
  npArtist.textContent = track.artist;
  npCover.innerHTML =
    typeof coverSvg === "function" ? coverSvg(track.cover || 0) : "";
  updateProgress(0, track.duration || 0);
  document.dispatchEvent(new CustomEvent("melo:track", { detail: track }));
}

function setSource(track) {
  if (hasSource(track)) {
    audio.src = track.src;
    audio.load();
  } else {
    audio.pause();
    audio.removeAttribute("src");
  }
}

// ---- simulation (placeholder tracks have no audio file) ----

function startSim() {
  stopSim();
  const track = currentTrack();
  const total = track ? track.duration || 0 : 0;
  simTimer = setInterval(() => {
    simTime += SIM_STEP;
    if (total && simTime >= total) {
      simTime = total;
      updateProgress(simTime, total);
      onEnded();
      return;
    }
    updateProgress(simTime, total);
  }, SIM_STEP * 1000);
}

function stopSim() {
  if (simTimer) {
    clearInterval(simTimer);
    simTimer = null;
  }
}

// ---- playback ----

function loadTrack(track, list) {
  if (!track) return;
  queue = Array.isArray(list) && list.length ? list : [track];
  index = queue.findIndex((t) => t.id === track.id);
  if (index < 0) {
    queue = [track];
    index = 0;
  }
  const active = currentTrack();
  stopSim();
  simTime = 0;
  setSource(active);
  renderNowPlaying(active);
  playTrack();
}

function playTrack() {
  const track = currentTrack();
  if (!track) return;
  if (hasSource(track)) {
    audio.play().catch(() => {});
  } else {
    startSim();
  }
  isPlaying = true;
  playPauseBtn.classList.add("is-playing");
  playPauseBtn.setAttribute("aria-label", "Pause");
}

function pauseTrack() {
  audio.pause();
  stopSim();
  isPlaying = false;
  playPauseBtn.classList.remove("is-playing");
  playPauseBtn.setAttribute("aria-label", "Play");
}

function togglePlay() {
  if (!currentTrack()) return;
  if (isPlaying) {
    pauseTrack();
  } else {
    playTrack();
  }
}

function onEnded() {
  if (repeat) {
    simTime = 0;
    if (hasSource(currentTrack())) {
      audio.currentTime = 0;
      audio.play().catch(() => {});
    } else {
      playTrack();
    }
    return;
  }
  nextTrack(true);
}

function nextTrack(fromEnded) {
  if (!queue.length) return;
  let next;
  if (shuffle && queue.length > 1) {
    do {
      next = Math.floor(Math.random() * queue.length);
    } while (next === index);
  } else {
    next = index + 1;
  }
  if (next >= queue.length) {
    if (fromEnded) {
      pauseTrack();
      return;
    }
    next = 0;
  }
  index = next;
  const track = currentTrack();
  stopSim();
  simTime = 0;
  setSource(track);
  renderNowPlaying(track);
  playTrack();
}

function prevTrack() {
  if (!queue.length) return;
  if ((hasSource(currentTrack()) ? audio.currentTime : simTime) > 3) {
    simTime = 0;
    if (hasSource(currentTrack())) audio.currentTime = 0;
    updateProgress(0, currentTrack().duration || 0);
    return;
  }
  index = index - 1 < 0 ? queue.length - 1 : index - 1;
  const track = currentTrack();
  stopSim();
  simTime = 0;
  setSource(track);
  renderNowPlaying(track);
  playTrack();
}

// ---- events ----

playPauseBtn.addEventListener("click", togglePlay);
prevBtn.addEventListener("click", prevTrack);
nextBtn.addEventListener("click", () => nextTrack(false));

shuffleBtn.addEventListener("click", () => {
  shuffle = !shuffle;
  shuffleBtn.setAttribute("aria-pressed", String(shuffle));
});

repeatBtn.addEventListener("click", () => {
  repeat = !repeat;
  repeatBtn.setAttribute("aria-pressed", String(repeat));
});

progressBar.addEventListener("input", () => {
  const track = currentTrack();
  if (!track) return;
  const total =
    hasSource(track) && isFinite(audio.duration) && audio.duration
      ? audio.duration
      : track.duration || 0;
  const target = (progressBar.value / 100) * total;
  if (hasSource(track)) {
    audio.currentTime = target;
  } else {
    simTime = target;
  }
  updateProgress(target, total);
});

audio.addEventListener("timeupdate", () => {
  const track = currentTrack();
  if (!hasSource(track)) return;
  updateProgress(audio.currentTime, audio.duration || track.duration || 0);
});

audio.addEventListener("loadedmetadata", () => {
  const track = currentTrack();
  if (track) updateProgress(audio.currentTime, audio.duration || track.duration || 0);
});

audio.addEventListener("ended", onEnded);

volumeSlider.addEventListener("input", () => {
  const value = Number(volumeSlider.value);
  audio.volume = value;
  setFill(volumeFill, value * 100);
});

audio.volume = Number(volumeSlider.value);
setFill(volumeFill, Number(volumeSlider.value) * 100);

document.addEventListener("keydown", (event) => {
  if (event.code !== "Space" && event.key !== " ") return;
  const el = event.target;
  const tag = el && el.tagName ? el.tagName.toLowerCase() : "";
  if (
    tag === "input" ||
    tag === "textarea" ||
    tag === "select" ||
    tag === "button" ||
    tag === "a" ||
    (el && el.isContentEditable)
  ) {
    return;
  }
  event.preventDefault();
  togglePlay();
});
