const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001/api/v1";

document.addEventListener('DOMContentLoaded', () => {
  const statusEl = document.getElementById('connection-status');
  const textEl = document.getElementById('status-text');
  const inputEl = document.getElementById('api-base-url');
  const saveEl = document.getElementById('save-config');
  
  const updateHealth = (apiBaseUrl) => {
    fetch(`${apiBaseUrl.replace(/\/$/, "")}/health`)
      .then(res => {
        if (res.ok) {
          statusEl.className = "status";
          textEl.innerText = "System Active";
        } else {
          throw new Error("Bad status");
        }
      })
      .catch(() => {
        statusEl.className = "status offline";
        textEl.innerText = "Backend Offline";
      });
  };

  chrome.storage.sync.get({ veritasApiBaseUrl: DEFAULT_API_BASE_URL }, ({ veritasApiBaseUrl }) => {
    inputEl.value = veritasApiBaseUrl;
    updateHealth(veritasApiBaseUrl);
  });

  saveEl.addEventListener('click', () => {
    const apiBaseUrl = inputEl.value.trim() || DEFAULT_API_BASE_URL;
    chrome.storage.sync.set({ veritasApiBaseUrl: apiBaseUrl }, () => {
      updateHealth(apiBaseUrl);
    });
  });
});
