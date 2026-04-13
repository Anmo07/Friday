document.addEventListener('DOMContentLoaded', () => {
  const statusEl = document.getElementById('connection-status');
  const textEl = document.getElementById('status-text');
  
  // Health check polling on the generic intelligence node correctly
  fetch("http://localhost:8000/api/v1/health")
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
});
