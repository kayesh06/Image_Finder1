document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const uploadBtn = document.getElementById('uploadBtn');
  const resultBox = document.getElementById('result');
  const folderInput = document.getElementById('folderId');
  const fileInput = document.getElementById('imageInput');

  const API_HOST = "http://127.0.0.1:8000";

  // Utility: show message in results
  function showMessage(message, type = "info") {
    resultBox.innerHTML = `<div class="${type} loading">${message}</div>`;
  }

  // Utility: show matches with simple fade-in effect
  function showMatches(matches, total) {
    let html = `<strong>${total} Matches Found:</strong><br>`;
    matches.forEach((m, i) => {
      html += `
        <div class="match" style="animation: fadeIn 0.3s ease ${i * 0.05}s forwards;opacity:0;">
          🖼️ ${m.name} — <b>Score:</b> ${m.score}<br>
          <a href="${m.link}" target="_blank">${m.link}</a>
        </div>
      `;
    });
    resultBox.innerHTML = html;
  }

  // CSS animation for fade-in
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
    .match { transform: translateY(10px); }
    .error { color: #d93025; font-weight: bold; text-align: center; }
    .info { color: #555; text-align: center; }
  `;
  document.head.appendChild(style);

  // Login with Google
  loginBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: `${API_HOST}/login/` });
  });

  // Upload and match
  uploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    let folderId = folderInput.value.trim();

    if (!file) {
      showMessage("⚠️ Please choose an image file.", "error");
      return;
    }
    if (!folderId) {
      showMessage("⚠️ Please enter folder ID or link.", "error");
      return;
    }

    // Extract folder ID if full link is pasted
    const match = folderId.match(/\/folders\/([a-zA-Z0-9_-]+)/);
    if (match) folderId = match[1];

    const fd = new FormData();
    fd.append('image', file);
    fd.append('folder_id', folderId);

    showMessage("⏳ Searching... please wait");

    try {
      const res = await fetch(`${API_HOST}/match-image/`, {
        method: "POST",
        body: fd,
        credentials: 'include'
      });

      if (res.status === 401) {
        showMessage("❌ Not logged in. Please click 'Sign in with Google'.", "error");
        return;
      }
      if (!res.ok) {
        const err = await res.text();
        showMessage("❌ Server error: " + err, "error");
        return;
      }

      const data = await res.json();
      if (!data.matches || data.matches.length === 0) {
        showMessage("No matches found.");
        return;
      }

      showMatches(data.matches, data.total_matches);
    } catch (e) {
      console.error(e);
      showMessage("❌ Fetch error: " + e.message, "error");
    }
  });
});
