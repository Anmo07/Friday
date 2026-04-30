const browserHostname = typeof window !== "undefined" ? window.location.hostname : "localhost";
const browserProtocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "https" : "http";
const wsProtocol = browserProtocol === "https" ? "wss" : "ws";
const backendPort = process.env.NEXT_PUBLIC_API_PORT || "8001";

const normalizeApiBase = (value: string) => value.replace(/\/$/, "").replace(/\/api\/v1$/, "");

const configuredApiOrigin =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  `${browserProtocol}://${browserHostname}:${backendPort}`;

const configuredWsBase =
  process.env.NEXT_PUBLIC_WS_BASE_URL ||
  process.env.NEXT_PUBLIC_WS_URL ||
  `${wsProtocol}://${browserHostname}:${backendPort}/ws/stream`;

export const API_BASE_URL = `${normalizeApiBase(configuredApiOrigin)}/api/v1`;
export const WS_BASE_URL = configuredWsBase.replace(/\/$/, "");

export const formatPercent = (value: number) => `${Math.round(Math.max(0, Math.min(value, 1)) * 100)}%`;

export const fetchHealthStatus = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    return await res.json();
  } catch (err) {
    console.error("API Gateway unreachable.");
    return null;
  }
};
