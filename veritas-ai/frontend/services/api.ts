export const API_BASE_URL = "http://localhost:8000/api/v1";
export const WS_BASE_URL = "ws://localhost:8000/ws/stream";

export const fetchHealthStatus = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    return await res.json();
  } catch (err) {
    console.error("API Gateway unreachable.");
    return null;
  }
};
