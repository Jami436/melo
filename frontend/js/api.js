// Central place for all calls to the Melo FastAPI backend.

const API_BASE_URL = "http://localhost:8000";

async function apiRequest(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

// Example usage once endpoints exist:
// const tracks = await apiRequest("/tracks");
