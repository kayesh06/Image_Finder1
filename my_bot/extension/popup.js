document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const uploadBtn = document.getElementById('uploadBtn');
  const historyBtn = document.getElementById('historyBtn'); // ✅ New history button
  const resultBox = document.getElementById('result');
  const folderInput = document.getElementById('folderId');
  const fileInput = document.getElementById('imageInput');

  const API_HOST = "http://127.0.0.1:8000";

  // Utility: show message in results
  function showMessage(message, type = "info") {
    resultBox.innerHTML = `<div class="${type}">${message}</div>`;
  }

  // Utility: show matches
  function showMatches(matches, total) {
    let html = `<strong>${total} Matches Found:</strong><br><br>`;
    matches.forEach((m) => {
      html += `
        <div style="margin-bottom:15px; padding:8px; border:1px solid #ccc; border-radius:8px; max-width:300px;">
            <img src="${m.thumbnail || ''}" alt="${m.name}"
                style="max-width:120px; border-radius:6px; display:block; margin-bottom:6px;" />
            🖼️ <strong>${m.name}</strong><br>
            🔢 Similarity Score: <strong>${m.score}</strong>
            <br><a href="${m.link}" target="_blank">[🔗 View in Drive]</a>
        </div>
      `;
    });
    resultBox.innerHTML = html;
  }

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

    // Extract folder ID if full link is pasted
    const match = folderId.match(/\/folders\/([a-zA-Z0-9_-]+)/);
    if (match) folderId = match[1];

    const fd = new FormData();
    fd.append('image', file);
    fd.append('folder_id', folderId); // can be empty now

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

  // Fetch search history
  if (historyBtn) {
    historyBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`${API_HOST}/get-history/`, {
          credentials: 'include'
        });
        const data = await res.json();

        if (!data.history || data.history.length === 0) {
          showMessage("📜 No search history found.", "info");
          return;
        }

        let html = "<h3>📜 Search History:</h3>";
        data.history.forEach((h, idx) => {
          html += `<div><strong>${idx + 1}. ${h.query_file}</strong> (${h.matches.length} matches)</div>`;
        });
        resultBox.innerHTML = html;
      } catch (e) {
        showMessage("❌ Error loading history: " + e.message, "error");
      }
    });
  }
});
