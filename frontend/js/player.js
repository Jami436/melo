// Handles the bottom audio player bar.

const audio = document.getElementById("audio-player");
const playPauseBtn = document.getElementById("play-pause-btn");
const nowPlaying = document.getElementById("now-playing");

let isPlaying = false;

function loadTrack(track) {
  // track = { title, artist, src }
  audio.src = track.src;
  nowPlaying.textContent = `${track.title} — ${track.artist}`;
  playTrack();
}

function playTrack() {
  audio.play();
  isPlaying = true;
  playPauseBtn.textContent = "⏸";
}

function pauseTrack() {
  audio.pause();
  isPlaying = false;
  playPauseBtn.textContent = "▶";
}

playPauseBtn.addEventListener("click", () => {
  if (isPlaying) {
    pauseTrack();
  } else {
    playTrack();
  }
});
