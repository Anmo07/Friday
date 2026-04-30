const DEFAULT_API_BASE_URL = "http://127.0.0.1:8001/api/v1";

async function getApiBaseUrl() {
  const stored = await chrome.storage.sync.get({ veritasApiBaseUrl: DEFAULT_API_BASE_URL });
  return String(stored.veritasApiBaseUrl || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "veritas-verify",
    title: "Verify Truth via Friday",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "veritas-verify" && info.selectionText) {
    if (tab && tab.id != null) {
      void (async () => {
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: displayLoadingOverlay
        });

        const apiBaseUrl = await getApiBaseUrl();
        try {
          const response = await fetch(`${apiBaseUrl}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: info.selectionText })
          });

          if (!response.ok) {
            throw new Error(`Verification failed with status ${response.status}`);
          }

          const data = await response.json();
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: displayResultOverlay,
            args: [data]
          });
        } catch (err) {
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: displayErrorOverlay,
            args: [String(err)]
          });
        }
      })();
    }
  }
});

// Stubs injected into the DOM autonomously dynamically via service worker
function displayLoadingOverlay() {
  window.dispatchEvent(new CustomEvent("veritas-loading"));
}

function displayResultOverlay(data) {
  window.dispatchEvent(new CustomEvent("veritas-result", { detail: data }));
}

function displayErrorOverlay(err) {
  window.dispatchEvent(new CustomEvent("veritas-error", { detail: err }));
}
