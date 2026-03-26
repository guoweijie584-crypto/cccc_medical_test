const DEFAULT_MEDICAL_API_PORT = "8001";
const LOOPBACK_ORIGINS = new Set(["5173", "8858"]);

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function getMedicalApiBase(): string {
  const originOverride = trimTrailingSlash(String(import.meta.env.VITE_MEDICAL_API_ORIGIN || "").trim());
  if (originOverride) return originOverride;

  if (typeof window === "undefined") {
    return `http://127.0.0.1:${DEFAULT_MEDICAL_API_PORT}`;
  }

  const configuredPort = String(import.meta.env.VITE_MEDICAL_API_PORT || "").trim() || DEFAULT_MEDICAL_API_PORT;
  const { origin, protocol, hostname, port } = window.location;

  // Local dev and direct CCCC web deployments keep the medical API on 8001.
  if (LOOPBACK_ORIGINS.has(port)) {
    return `${protocol}//${hostname}:${configuredPort}`;
  }

  // When the UI is behind a reverse proxy on 80/443, prefer same-origin `/api`.
  return trimTrailingSlash(origin);
}

export function medicalApiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getMedicalApiBase()}${normalizedPath}`;
}
