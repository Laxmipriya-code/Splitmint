const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1";
const HEALTH_PING_INTERVAL_MS = 5 * 60 * 1000;

function resolveHealthUrl() {
  const apiBaseUrl = (
    import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL
  ).replace(/\/+$/, "");

  if (apiBaseUrl.endsWith("/api/v1")) {
    return `${apiBaseUrl.slice(0, -"/api/v1".length)}/health`;
  }

  return `${apiBaseUrl}/health`;
}

const HEALTH_URL = resolveHealthUrl();

async function pingBackendHealth() {
  try {
    await fetch(HEALTH_URL, {
      method: "GET",
      cache: "no-store",
      keepalive: true,
    });
  } catch {
    // Keep-alive is best effort; ignore transient network failures.
  }
}

export function startBackendHealthKeepAlive() {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  void pingBackendHealth();
  const intervalId = window.setInterval(() => {
    void pingBackendHealth();
  }, HEALTH_PING_INTERVAL_MS);

  return () => {
    window.clearInterval(intervalId);
  };
}
