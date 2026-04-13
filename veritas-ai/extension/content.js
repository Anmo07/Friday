let overlay = null;

function createOverlay() {
  if (overlay) return overlay;

  overlay = document.createElement('div');
  overlay.id = 'veritas-ai-overlay';
  
  const closeBtn = document.createElement('button');
  closeBtn.innerText = '✕';
  closeBtn.className = 'veritas-close';
  closeBtn.onclick = () => { overlay.style.display = 'none'; };

  const content = document.createElement('div');
  content.id = 'veritas-content';

  overlay.appendChild(closeBtn);
  overlay.appendChild(content);
  document.body.appendChild(overlay);

  return overlay;
}

window.addEventListener("veritas-loading", () => {
    const el = createOverlay();
    el.style.display = 'block';
    const content = el.querySelector('#veritas-content');
    content.innerHTML = `
      <div class="veritas-loader"></div>
      <h3 style="color:#60A5FA; margin-top:15px; font-family:sans-serif;">Veritas Intelligence</h3>
      <p style="color:#d1d5db; font-size:14px;">Orchestrating mathematical verification...</p>
    `;
});

window.addEventListener("veritas-result", (e) => {
    const data = e.detail;
    const el = createOverlay();
    const content = el.querySelector('#veritas-content');
    
    let statusColor = "#3B82F6";
    if(data.status === "verified") statusColor = "#10B981";
    if(data.status === "likely_false") statusColor = "#EF4444";
    if(data.status === "uncertain") statusColor = "#F59E0B";

    content.innerHTML = `
      <h3 style="color:${statusColor}; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; margin-bottom: 5px;">${data.status}</h3>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 15px;">
        <span style="font-size:32px; font-weight:bold; color:white;">${data.truth_score}% <span style="font-size:12px; font-weight:normal; color:#9ca3af;">Truth Score</span></span>
        <span style="font-size:20px; font-weight:bold; color:#fca5a5;">${data.fake_probability}% <span style="font-size:12px; font-weight:normal; color:#9ca3af;">Bias</span></span>
      </div>
      <p style="color:#e5e7eb; font-size:14px; line-height:1.5;">${data.summary}</p>
      
      <div style="margin-top:10px; padding:10px; background:rgba(0,0,0,0.3); border-radius:8px;">
        <strong style="color:${statusColor}; font-size:12px;">AUTHORITY PATTERN:</strong>
        <p style="color:#d1d5db; font-size:12px; margin:3px 0;">${data.explanation?.confidence_breakdown?.authority || "No explicit authority extracted."}</p>
      </div>
    `;
});

window.addEventListener("veritas-error", (e) => {
    const el = createOverlay();
    const content = el.querySelector('#veritas-content');
    content.innerHTML = `
      <h3 style="color:#EF4444;">Verification Failed</h3>
      <p style="color:#d1d5db;">${e.detail}</p>
    `;
});
