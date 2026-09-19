// Pragati Bharati Document Intelligence Dashboard Logic
const API_BASE = "/api/v1";
let authToken = localStorage.getItem("pb_token") || null;
let currentUser = null;
let currentDocuments = [];
let activeDocument = null;
let activeQuestions = [];
let activeFilter = "ALL";
let statusPollInterval = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupDropZone();
  setupDocRoleListener();
  if (authToken) {
    fetchUserProfile();
  } else {
    // Auto-login with demo credentials for seamless first-time experience
    autoLoginDemo();
  }
});

function setupDropZone() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  ["dragleave", "dragend"].forEach((type) => {
    dropZone.addEventListener(type, () => dropZone.classList.remove("dragover"));
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      updateFileLabel(fileInput.files[0].name);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      updateFileLabel(fileInput.files[0].name);
    }
  });

  document.getElementById("uploadForm").addEventListener("submit", handleUploadSubmit);
}

function updateFileLabel(name) {
  document.querySelector(".drop-title").innerText = name;
  document.querySelector(".drop-sub").innerText = "File selected. Click Ingest to process.";
}

function setupDocRoleListener() {
  const docRole = document.getElementById("docRole");
  const relateGroup = document.getElementById("relateGroup");
  docRole.addEventListener("change", () => {
    if (docRole.value === "ANSWER_KEY") {
      relateGroup.style.display = "block";
      populateTargetDocSelect();
    } else {
      relateGroup.style.display = "none";
    }
  });
}

function populateTargetDocSelect() {
  const sel = document.getElementById("targetDocSelect");
  sel.innerHTML = '<option value="">-- None (Standalone) --</option>';
  currentDocuments
    .filter((d) => d.document_role === "QUESTION_PAPER")
    .forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.innerText = `${d.original_filename} (${d.total_questions} Qs)`;
      sel.appendChild(opt);
    });
}

// Authentication Handlers
async function autoLoginDemo() {
  try {
    const res = await fetch(`${API_BASE}/auth/login/json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "evaluator@pragatibharati.in",
        password: "EvaluatorPassword123!"
      })
    });
    if (res.ok) {
      const data = await res.json();
      setAuth(data.access_token, data.user);
    }
  } catch (e) {
    console.log("Demo auto-login waiting for user registration.");
  }
}

function setAuth(token, user) {
  authToken = token;
  currentUser = user;
  localStorage.setItem("pb_token", token);
  document.getElementById("userBadge").innerText = `👤 ${user.username}`;
  document.getElementById("authBtn").innerText = "Logout";
  document.getElementById("authBtn").onclick = logout;
  loadDocuments();
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem("pb_token");
  document.getElementById("userBadge").innerText = "Not Logged In";
  document.getElementById("authBtn").innerText = "Login / Register";
  document.getElementById("authBtn").onclick = openAuthModal;
  currentDocuments = [];
  renderDocList();
}

async function fetchUserProfile() {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (res.ok) {
      const user = await res.json();
      setAuth(authToken, user);
    } else {
      logout();
    }
  } catch (e) {
    logout();
  }
}

function openAuthModal() {
  document.getElementById("authModal").classList.add("open");
}
function closeAuthModal() {
  document.getElementById("authModal").classList.remove("open");
}

let activeAuthTab = "login";
function switchAuthTab(tab) {
  activeAuthTab = tab;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  event.target.classList.add("active");
  document.getElementById("usernameGroup").style.display = tab === "register" ? "block" : "none";
  document.getElementById("authSubmitBtn").innerText = tab === "register" ? "Create Account" : "Login";
}

function fillQuickDemoUser() {
  document.getElementById("authEmail").value = "evaluator@pragatibharati.in";
  document.getElementById("authPassword").value = "EvaluatorPassword123!";
  if (activeAuthTab === "register") {
    document.getElementById("authUsername").value = "evaluator";
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value;
  const password = document.getElementById("authPassword").value;
  const username = document.getElementById("authUsername").value;

  if (activeAuthTab === "register") {
    const regRes = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password })
    });
    if (!regRes.ok) {
      const err = await regRes.json();
      alert(`Registration failed: ${err.detail}`);
      return;
    }
  }

  // Login
  const loginRes = await fetch(`${API_BASE}/auth/login/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });

  if (loginRes.ok) {
    const data = await loginRes.json();
    setAuth(data.access_token, data.user);
    closeAuthModal();
  } else {
    const err = await loginRes.json();
    alert(`Login failed: ${err.detail}`);
  }
}

// Upload & Document Management
async function handleUploadSubmit(e) {
  e.preventDefault();
  if (!authToken) {
    openAuthModal();
    return;
  }

  const fileInput = document.getElementById("fileInput");
  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("document_role", document.getElementById("docRole").value);
  const targetId = document.getElementById("targetDocSelect").value;
  if (targetId) {
    formData.append("target_document_id", targetId);
  }

  const btn = document.getElementById("submitUploadBtn");
  btn.disabled = true;
  btn.innerHTML = "<span>Uploading & Queueing...</span>";

  try {
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      fileInput.value = "";
      document.querySelector(".drop-title").innerText = "Drag & drop files here";
      document.querySelector(".drop-sub").innerText = "or click to browse from device";
      startStatusPolling(data.document_id, data.original_filename);
      await loadDocuments();
    } else {
      const err = await res.json();
      alert(`Upload error: ${err.detail}`);
    }
  } catch (err) {
    alert(`Network error: ${err}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "<span>Ingest & Extract Asynchronously</span>";
  }
}

async function loadDocuments() {
  if (!authToken) return;
  try {
    const res = await fetch(`${API_BASE}/documents`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (res.ok) {
      currentDocuments = await res.json();
      renderDocList();
      populateTargetDocSelect();
    }
  } catch (e) {
    console.error("Failed to load documents", e);
  }
}

function renderDocList() {
  const container = document.getElementById("docListContainer");
  if (!currentDocuments.length) {
    container.innerHTML = '<p class="empty-state">No documents uploaded yet.</p>';
    return;
  }

  container.innerHTML = currentDocuments
    .map(
      (d) => `
      <div class="doc-item ${activeDocument && activeDocument.id === d.id ? "active" : ""}" onclick="selectDocument('${d.id}')">
        <div class="doc-info">
          <h4>${d.original_filename}</h4>
          <span>${d.document_type} • ${d.page_count} pages • ${d.total_questions} Qs</span>
        </div>
        <span class="status-pill status-${d.status.toLowerCase()}">${d.status}</span>
      </div>
    `
    )
    .join("");
}

// Polling & Status Tracking
function startStatusPolling(docId, filename) {
  if (statusPollInterval) clearInterval(statusPollInterval);

  const statusCard = document.getElementById("statusCard");
  statusCard.style.display = "block";
  document.getElementById("activeDocTitle").innerText = filename;
  document.getElementById("activeDocId").innerText = `ID: ${docId.substring(0, 8)}...`;

  const poll = async () => {
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/status`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) {
        const s = await res.json();
        updateStatusBar(s);
        if (s.status === "COMPLETED" || s.status === "FAILED") {
          clearInterval(statusPollInterval);
          loadDocuments();
          if (s.status === "COMPLETED") {
            selectDocument(docId);
          }
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  poll();
  statusPollInterval = setInterval(poll, 1500);
}

function updateStatusBar(s) {
  const badge = document.getElementById("activeDocBadge");
  badge.className = `status-pill status-${s.status.toLowerCase()}`;
  badge.innerText = s.status;

  const bar = document.getElementById("progressBar");
  bar.style.width = `${s.progress_percent}%`;
  document.getElementById("progressText").innerText = `${s.progress_percent}%`;

  if (s.status === "PROCESSING") {
    document.getElementById("statusMessage").innerText = "Extracting text, questions & answer keys...";
  } else if (s.status === "COMPLETED") {
    document.getElementById("statusMessage").innerText = `Done! Found ${s.total_questions} questions (${s.confident_questions} confident).`;
  } else if (s.status === "FAILED") {
    document.getElementById("statusMessage").innerText = `Failed: ${s.error_message || "Unknown error"}`;
  }
}

// Question Viewer & Filters
async function selectDocument(docId) {
  activeDocument = currentDocuments.find((d) => d.id === docId);
  renderDocList();

  try {
    const res = await fetch(`${API_BASE}/documents/${docId}/questions`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      activeQuestions = data.questions;
      updateFilterCounts();
      renderQuestions();
      document.getElementById("filterActions").style.display = "flex";
      document.getElementById("resultsMeta").innerText = `${activeDocument.original_filename} (${activeDocument.page_count} pages, OCR: ${activeDocument.ocr_method_used})`;
    }
  } catch (e) {
    console.error("Error loading questions", e);
  }
}

function updateFilterCounts() {
  document.getElementById("countAll").innerText = activeQuestions.length;
  document.getElementById("countConfident").innerText = activeQuestions.filter((q) => q.confidence_level === "CONFIDENT").length;
  document.getElementById("countReview").innerText = activeQuestions.filter((q) => q.confidence_level !== "CONFIDENT").length;
}

function filterQuestions(filter) {
  activeFilter = filter;
  document.querySelectorAll(".btn-filter").forEach((b) => b.classList.remove("active"));
  event.target.classList.add("active");
  renderQuestions();
}

function renderQuestions() {
  const container = document.getElementById("questionsContainer");
  let filtered = activeQuestions;

  if (activeFilter === "CONFIDENT") {
    filtered = activeQuestions.filter((q) => q.confidence_level === "CONFIDENT");
  } else if (activeFilter === "NEEDS_REVIEW") {
    filtered = activeQuestions.filter((q) => q.confidence_level !== "CONFIDENT");
  }

  if (!filtered.length) {
    container.innerHTML = '<p class="empty-state">No questions found matching this filter.</p>';
    return;
  }

  container.innerHTML = filtered
    .map((q) => {
      const isReview = q.confidence_level !== "CONFIDENT";
      const confClass = q.confidence_level === "CONFIDENT" ? "status-completed" : "status-pending";

      const optionsHtml = q.options && q.options.length
        ? `<div class="options-grid">
            ${q.options
              .map(
                (opt) => `
              <div class="option-item ${opt.is_correct ? "correct" : ""}">
                <span class="opt-badge">${opt.option_key}</span>
                <span>${opt.option_text}</span>
                ${opt.is_correct ? "<span>✓</span>" : ""}
              </div>
            `
              )
              .join("")}
          </div>`
        : "";

      const reasonsHtml = q.review_reasons && q.review_reasons.length
        ? `<div class="review-reasons-pill">⚠️ ${q.review_reasons.join(", ")}</div>`
        : "";

      const pagesHtml = (q.source_pages || [1])
        .map(
          (p) => `<span class="badge-pages" onclick="openPagePreview('${q.document_id}', ${p})">Page ${p}</span>`
        )
        .join(" ");

      return `
      <div class="question-card">
        <div class="q-header">
          <div>
            <span class="code-badge">${q.raw_number_label || `Q${q.question_number || "?"}`}</span>
            <span class="status-pill ${confClass}">${q.confidence_level} (${Math.round(q.confidence_score * 100)}%)</span>
          </div>
          <div>${reasonsHtml}</div>
        </div>
        <div class="q-title">${q.question_text}</div>
        ${optionsHtml}
        <div class="q-footer">
          <div>
            ${q.detected_answer ? `<strong>Answer:</strong> <span class="badge-accent">${q.detected_answer}</span> (${q.answer_source || "auto"})` : '<span class="text-muted">No answer key associated</span>'}
          </div>
          <div>
            <strong>Source:</strong> ${pagesHtml}
          </div>
        </div>
      </div>
    `;
    })
    .join("");
}

// Page Preview Modal
function openPagePreview(docId, pageNum) {
  const modal = document.getElementById("previewModal");
  const img = document.getElementById("previewImage");
  document.getElementById("previewTitle").innerText = `Document Source - Page ${pageNum}`;
  img.src = `${API_BASE}/documents/${docId}/page-preview/${pageNum}`;
  modal.classList.add("open");
}

function closePreviewModal() {
  document.getElementById("previewModal").classList.remove("open");
}

// JSON Export
async function exportJson() {
  if (!activeDocument) return;
  try {
    const res = await fetch(`${API_BASE}/documents/${activeDocument.id}/export`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeDocument.original_filename}_extracted.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  } catch (e) {
    alert("Export failed: " + e);
  }
}
