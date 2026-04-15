let overlay = null;

function clampScore(value) {
  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return "N/A";
  }
  return `${Math.round(Math.max(0, Math.min(numericValue, 1)) * 100)}%`;
}

function clearContent(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function appendTextElement(parent, tag, text, styles = {}) {
  const element = document.createElement(tag);
  element.textContent = text;
  Object.assign(element.style, styles);
  parent.appendChild(element);
  return element;
}

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
    clearContent(content);

    const loader = document.createElement("div");
    loader.className = "veritas-loader";
    content.appendChild(loader);
    appendTextElement(content, "h3", "Veritas Intelligence", {
      color: "#60A5FA",
      marginTop: "15px",
      fontFamily: "sans-serif"
    });
    appendTextElement(content, "p", "Running verification...", {
      color: "#d1d5db",
      fontSize: "14px"
    });
});

window.addEventListener("veritas-result", (e) => {
    const data = e.detail;
    const el = createOverlay();
    const content = el.querySelector('#veritas-content');
    clearContent(content);
    
    let statusColor = "#3B82F6";
    if(data.status === "verified") statusColor = "#10B981";
    if(data.status === "likely_false") statusColor = "#EF4444";
    if(data.status === "uncertain") statusColor = "#F59E0B";

    appendTextElement(content, "h3", data.status || "uncertain", {
      color: statusColor,
      fontFamily: "sans-serif",
      textTransform: "uppercase",
      letterSpacing: "1px",
      marginBottom: "5px"
    });

    const stats = document.createElement("div");
    Object.assign(stats.style, {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "15px"
    });
    appendTextElement(stats, "span", `${clampScore(data.truth_score)} Truth Score`, {
      fontSize: "20px",
      fontWeight: "bold",
      color: "white"
    });
    appendTextElement(stats, "span", `${clampScore(data.fake_probability)} Bias`, {
      fontSize: "18px",
      fontWeight: "bold",
      color: "#fca5a5"
    });
    content.appendChild(stats);

    appendTextElement(content, "p", data.summary || "No summary available.", {
      color: "#e5e7eb",
      fontSize: "14px",
      lineHeight: "1.5"
    });

    const authorityPanel = document.createElement("div");
    Object.assign(authorityPanel.style, {
      marginTop: "10px",
      padding: "10px",
      background: "rgba(0,0,0,0.3)",
      borderRadius: "8px"
    });
    appendTextElement(authorityPanel, "strong", "AUTHORITY PATTERN:", {
      color: statusColor,
      fontSize: "12px"
    });
    appendTextElement(
      authorityPanel,
      "p",
      String(data.explanation?.confidence_breakdown?.authority ?? "No explicit authority extracted."),
      { color: "#d1d5db", fontSize: "12px", margin: "3px 0 0" }
    );
    content.appendChild(authorityPanel);
});

window.addEventListener("veritas-error", (e) => {
    const el = createOverlay();
    const content = el.querySelector('#veritas-content');
    clearContent(content);
    appendTextElement(content, "h3", "Verification Failed", { color: "#EF4444" });
    appendTextElement(content, "p", String(e.detail), { color: "#d1d5db" });
});
