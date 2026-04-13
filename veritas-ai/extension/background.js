chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "veritas-verify",
    title: "Verify Truth via Veritas AI",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "veritas-verify" && info.selectionText) {
    if (tab && tab.id != null) {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: displayLoadingOverlay
      });

      fetch("http://localhost:8000/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: info.selectionText })
      })
      .then(res => res.json())
      .then(data => {
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: displayResultOverlay,
          args: [data]
        });
      })
      .catch(err => {
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: displayErrorOverlay,
          args: [err.toString()]
        });
      });
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
