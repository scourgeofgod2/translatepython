/* mirapdf — tab router + upload flow */
import { initJobs, refreshJobs } from "./jobs.js";
import { initSettings, loadSettings } from "./settings.js";

const tabs = ["translate", "jobs", "settings"];

function showTab(name) {
  for (const t of tabs) {
    const panel = document.getElementById(`tab-${t}`);
    const btn = document.querySelector(`.nav-btn[data-tab="${t}"]`);
    if (panel) panel.classList.toggle("active", t === name);
    if (btn) btn.classList.toggle("active", t === name);
  }
  if (name === "jobs") refreshJobs();
  if (name === "settings") loadSettings();
}

function initTabs() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => showTab(btn.dataset.tab));
  });
  const shortcut = document.getElementById("btn-settings-shortcut");
  if (shortcut) shortcut.addEventListener("click", () => showTab("settings"));
}

function showBanner(id, message, ok = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `banner show ${ok ? "banner-ok" : "banner-err"}`;
  if (ok && id === "translate-info") el.className = "banner show banner-info";
}

function hideBanner(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("show");
}

function initUpload() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileLabel = document.getElementById("file-label");
  const btnStart = document.getElementById("btn-start");
  let selectedFile = null;

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files?.[0]) setFile(fileInput.files[0]);
  });

  function setFile(f) {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      showBanner("translate-error", "Sadece PDF dosyaları destekleniyor.");
      return;
    }
    if (f.size > 80 * 1024 * 1024) {
      showBanner("translate-error", "Dosya çok büyük (maks 80 MB).");
      return;
    }
    hideBanner("translate-error");
    selectedFile = f;
    fileLabel.textContent = `${f.name} · ${(f.size / 1024 / 1024).toFixed(1)} MB`;
    updateStartBtn();
  }

  function updateStartBtn() {
    // enabled if file selected; API key check happens at submit
    btnStart.disabled = !selectedFile;
  }

  btnStart.addEventListener("click", async () => {
    if (!selectedFile) return;
    hideBanner("translate-error");
    hideBanner("translate-info");
    btnStart.disabled = true;
    btnStart.textContent = "Yükleniyor…";

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("lang_in", document.getElementById("opt-lang-in").value);
    formData.append("lang_out", document.getElementById("opt-lang-out").value);
    formData.append("pages", document.getElementById("opt-pages").value);
    formData.append("threads", document.getElementById("opt-threads").value || "4");
    formData.append("model", document.getElementById("opt-model").value);
    formData.append("prompt_override", document.getElementById("opt-prompt").value);
    formData.append("ignore_cache", document.getElementById("opt-ignore-cache").checked ? "true" : "false");

    try {
      const resp = await fetch("/api/jobs", { method: "POST", body: formData });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = data.detail || `Hata ${resp.status}`;
        showBanner("translate-error", typeof detail === "string" ? detail : JSON.stringify(detail));
        if (resp.status === 400 && String(detail).includes("API")) {
          showTab("settings");
        }
        return;
      }
      selectedFile = null;
      fileLabel.textContent = "";
      fileInput.value = "";
      showBanner("translate-info", "İş oluşturuldu. İlerlemeyi İşler sekmesinden izleyin.", true);
      showTab("jobs");
      refreshJobs();
    } catch (e) {
      showBanner("translate-error", `Bağlantı hatası: ${e.message}`);
    } finally {
      btnStart.textContent = "Çeviriyi Başlat";
      updateStartBtn();
    }
  });

  // load default prompt into textarea
  fetch("/api/settings")
    .then((r) => r.json())
    .then((s) => {
      const ta = document.getElementById("opt-prompt");
      if (ta && s.default_prompt && !ta.value) ta.placeholder = s.default_prompt.slice(0, 120) + "…";
    })
    .catch(() => {});
}

// App init
initTabs();
initUpload();
initSettings();
initJobs();
