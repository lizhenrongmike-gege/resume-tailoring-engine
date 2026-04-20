const API = JOBCAPTURE_CONFIG.API_BASE_URL;
let currentJobData = null;
let isExpanded = false;

document.addEventListener("DOMContentLoaded", async () => {
  await loadDetectedJob();
  await loadBatch();

  document.getElementById("btnSave").addEventListener("click", saveJob);
  document.getElementById("btnFinish").addEventListener("click", finishBatch);
  document.getElementById("expandToggle").addEventListener("click", toggleExpand);
  document.getElementById("linkDashboard").addEventListener("click", () => {
    chrome.tabs.create({ url: "http://localhost:5173" });
  });
});

async function loadDetectedJob() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Inject content script if not already present (for non-LinkedIn pages)
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["config.js", "content.js"],
      });
    } catch (e) {
      // May fail if already injected or on restricted pages — that's fine
    }

    // Small delay to let the script initialize
    await new Promise((r) => setTimeout(r, 100));

    const response = await chrome.tabs.sendMessage(tab.id, { action: "getJobData" });
    if (response && response.company) {
      currentJobData = response;
      document.getElementById("detectedCompany").textContent = response.company;
      document.getElementById("detectedTitle").textContent = response.title || "Unknown Role";
      document.getElementById("locationText").textContent = response.location || "—";
      if (response.team) {
        document.getElementById("teamText").textContent = response.team;
        document.getElementById("detectedTeam").style.display = "flex";
      }
      document.getElementById("btnSave").disabled = false;
    }
  } catch (e) {
    // Not on a LinkedIn job page
  }
}

async function loadBatch() {
  try {
    const resp = await fetch(`${API}/api/jobs?status=active_batch`);
    const jobs = await resp.json();
    renderBatch(jobs);
  } catch (e) {
    console.error("Failed to load batch:", e);
  }
}

function renderBatch(jobs) {
  const list = document.getElementById("batchList");
  const empty = document.getElementById("emptyBatch");
  const countBadge = document.getElementById("batchCount");
  const finishBtn = document.getElementById("btnFinish");

  countBadge.textContent = `${jobs.length} in batch`;
  finishBtn.disabled = jobs.length === 0;

  if (jobs.length === 0) {
    list.innerHTML = "";
    list.appendChild(empty);
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  list.innerHTML = jobs
    .map((job) => {
      const meta =
        isExpanded && (job.location || job.team)
          ? `<div class="batch-meta">${[job.location, job.team].filter(Boolean).join(" · ")}</div>`
          : "";
      return `
        <div class="batch-item${isExpanded ? " expanded-item" : ""}" data-id="${job.id}">
          <div class="batch-item-info">
            <div class="batch-company">${job.company}</div>
            <div class="batch-role">${job.title}</div>
            ${meta}
          </div>
          <span class="batch-delete" data-id="${job.id}">×</span>
        </div>`;
    })
    .join("");

  list.querySelectorAll(".batch-delete").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.dataset.id;
      await fetch(`${API}/api/jobs/${id}`, { method: "DELETE" });
      await loadBatch();
    });
  });
}

async function saveJob() {
  if (!currentJobData) return;
  const btn = document.getElementById("btnSave");
  btn.disabled = true;
  btn.textContent = "Saving...";

  try {
    await fetch(`${API}/api/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentJobData),
    });
    btn.textContent = "Saved ✓";
    btn.classList.add("saved");
    await loadBatch();
  } catch (e) {
    btn.textContent = "Error — retry";
    btn.disabled = false;
  }
}

async function finishBatch() {
  const btn = document.getElementById("btnFinish");
  btn.disabled = true;
  btn.textContent = "Finishing...";

  try {
    const resp = await fetch(`${API}/api/batches/finish`, { method: "POST" });
    if (resp.ok) {
      btn.textContent = "Done ✓";
      await loadBatch();
    } else {
      const err = await resp.json();
      btn.textContent = err.detail || "Error";
      btn.disabled = false;
    }
  } catch (e) {
    btn.textContent = "Error — retry";
    btn.disabled = false;
  }
}

function toggleExpand() {
  isExpanded = !isExpanded;
  document.getElementById("expandText").textContent = isExpanded ? "▲ Collapse" : "▼ Expand";

  const batchList = document.getElementById("batchList");
  if (isExpanded) {
    batchList.style.maxHeight = "none";
  } else {
    batchList.style.maxHeight = "140px";
  }

  loadBatch();
}
