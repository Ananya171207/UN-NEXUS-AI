// Connection settings for the Python (FastAPI) backend in /backend.
//
// RESEARCH ASSISTANT: always talks to the real backend. It uses VITE_API_URL
// when set, otherwise http://localhost:8000 (the backend's default port).
//
// SITUATION ROOM: its endpoints (/api/countries, /api/events) are not built
// yet, so it keeps using built-in SAMPLE data while VITE_API_URL is unset.
// (Setting VITE_API_URL switches the Situation Room to those endpoints too.)
//
// To change the backend address, create `.env` in the frontend folder:
//
//   VITE_API_URL=http://localhost:8000
//
// and restart the dev server. API keys NEVER go in the frontend.

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';
export const USE_SAMPLE_DATA = API_BASE_URL === '';
export const RESEARCH_API_BASE_URL = API_BASE_URL || 'http://localhost:8000';

// Waits `ms`. If an AbortSignal is given and fires, the wait ends early with an AbortError.
export const delay = (ms, signal) =>
  new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const id = setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(id);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true }
    );
  });

export async function apiGet(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal: options.signal });
  if (!response.ok) {
    throw new Error(`The server answered with an error (${response.status}).`);
  }
  return response.json();
}

export async function apiPost(path, body, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: options.signal,
  });
  if (!response.ok) {
    throw new Error(`The server answered with an error (${response.status}).`);
  }
  return response.json();
}
