/* Jobs list + progress polling */

const STATUS_LABEL = {
  queued: "Sırada",
  running: "Çeviriliyor",
  done: "Tamamlandı",
  failed: "Başarısız",
  canceled: "İptal",
};

const STAGE_LABEL = {
  queued: "Sırada",
  loading_model: "Model yükleniyor",
  translating: "Çeviriliyor",
  writing_pdf: "PDF yazılıyor",
  finished: "Bitti",
  failed: "Hata",
  canceled: "İptal edildi",
};

let pollTimer = null;

export function initJobs() {
  refreshJobs();
  startPolling();
}

export function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    const jobsPanel = document.getElementById("tab-jobs");
    if (jobsPanel && jobsPanel.classList.contains("active")) {
      refreshJobs();
    }
  }, 2000);
}

export async function refreshJobs() {
  const list = document.getElementById("jobs-list");
  if (!list) return;
  try {
    const resp = await fetch("/api/jobs");
    if (!resp.ok) return;
    const jobs = await resp.json();
    if (!jobs.length) {
      list.innerHTML = `<div class="empty">Henüz iş yok. Çeviri sekmesinden bir PDF yükleyin.</div>`;
      return;
    }
    list.innerHTML = jobs.map(renderJob).join("");
    bindJobActions();
  } catch {
    /* ignore network blips */
  }
}

function renderJob(job) {
  const status = job.status || "queued";
  const pct = Math.round((job.progress || 0) * 100);
  const stage = STAGE_LABEL[job.stage] || job.stage || "";
  const created = job.created_at ? new Date(job.created_at).toLocaleString("tr-TR") : "";
  const pages =
    job.pages_total != null ? `${job.pages_done ?? 0}/${job.pages_total} sayfa` : "";

  let actions = "";
  if (status === "done" && job.output_mono) {
    actions += `<a class="btn btn-primary btn-sm" href="/api/jobs/${job.id}/download">İndir (PDF)</a>`;
  }
  if (status === "running" || status === "queued") {
    actions += `<button class="btn btn-danger btn-sm" data-action="cancel" data-id="${job.id}">İptal / Sil</button>`;
  } else {
    actions += `<button class="btn btn-secondary btn-sm" data-action="log" data-id="${job.id}">Günlük</button>`;
    actions += `<button class="btn btn-danger btn-sm" data-action="delete" data-id="${job.id}">Sil</button>`;
  }

  const errorBlock = job.error
    ? `<div style="color:var(--err);font-size:0.88rem;margin-bottom:0.5rem">${escapeHtml(job.error)}</div>`
    : "";

  return `
    <div class="job-card" id="job-${job.id}">
      <div class="header">
        <div class="filename" title="${escapeHtml(job.filename)}">${escapeHtml(job.filename)}</div>
        <span class="badge badge-${status}">${STATUS_LABEL[status] || status}</span>
      </div>
      <div class="meta">
        <span>${stage}</span>
        ${pages ? `<span>${pages}</span>` : ""}
        <span>${created}</span>
      </div>
      ${errorBlock}
      <div class="progress-track">
        <div class="progress-bar" style="width:${status === "done" ? 100 : pct}%"></div>
      </div>
      <div class="job-actions">${actions}</div>
      <div class="log-box" id="log-${job.id}"></div>
    </div>
  `;
}

function bindJobActions() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const action = btn.dataset.action;
      if (action === "delete" || action === "cancel") {
        if (!confirm("Bu işi silmek istediğinize emin misiniz?")) return;
        await fetch(`/api/jobs/${id}`, { method: "DELETE" });
        refreshJobs();
      } else if (action === "log") {
        const box = document.getElementById(`log-${id}`);
        if (!box) return;
        if (box.classList.contains("show")) {
          box.classList.remove("show");
          return;
        }
        const resp = await fetch(`/api/jobs/${id}/log`);
        box.textContent = await resp.text();
        box.classList.add("show");
      }
    });
  });
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
