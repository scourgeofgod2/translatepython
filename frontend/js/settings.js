/* Settings form + connection test */

function normalizeBaseUrl(url) {
  url = (url || "").trim().replace(/\/+$/, "");
  if (!url) return "https://app.claude.gg/v1";
  if (!url.endsWith("/v1")) url += "/v1";
  return url;
}

export async function loadSettings() {
  try {
    const resp = await fetch("/api/settings");
    if (!resp.ok) return;
    const s = await resp.json();

    setVal("set-base-url", s.base_url);
    setVal("set-model", s.model);
    setVal("set-threads", s.threads);
    setVal("set-lang-in", s.lang_in);
    setVal("set-lang-out", s.lang_out);
    setVal("set-hf", s.hf_endpoint);

    const keyStatus = document.getElementById("api-key-status");
    const keyInput = document.getElementById("set-api-key");
    if (keyStatus) {
      keyStatus.textContent = s.api_key_set
        ? "Kayıtlı anahtar mevcut (değiştirmek için yeni değer girin)"
        : "Kayıtlı anahtar yok";
    }
    if (keyInput && s.api_key_set) {
      keyInput.placeholder = "•••••••• (kayıtlı)";
    }

    updatePreview();
  } catch {
    /* ignore */
  }
}

function setVal(id, value) {
  const el = document.getElementById(id);
  if (el && value != null) el.value = value;
}

function updatePreview() {
  const input = document.getElementById("set-base-url");
  const preview = document.getElementById("base-url-preview");
  if (input && preview) {
    preview.textContent = normalizeBaseUrl(input.value);
  }
}

export function initSettings() {
  const baseInput = document.getElementById("set-base-url");
  if (baseInput) baseInput.addEventListener("input", updatePreview);

  const btnTest = document.getElementById("btn-test");
  if (btnTest) btnTest.addEventListener("click", onTest);

  const btnSave = document.getElementById("btn-save");
  if (btnSave) btnSave.addEventListener("click", onSave);

  loadSettings();
}

function showBanner(id, message, ok) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `banner show ${ok ? "banner-ok" : "banner-err"}`;
}

function hideBanner(id) {
  document.getElementById(id)?.classList.remove("show");
}

async function onSave() {
  hideBanner("settings-ok");
  hideBanner("settings-err");

  const body = {
    base_url: normalizeBaseUrl(document.getElementById("set-base-url").value),
    model: document.getElementById("set-model").value,
    threads: parseInt(document.getElementById("set-threads").value, 10) || 4,
    lang_in: document.getElementById("set-lang-in").value.trim() || "en",
    lang_out: document.getElementById("set-lang-out").value.trim() || "tr",
    hf_endpoint: document.getElementById("set-hf").value.trim(),
  };
  const key = document.getElementById("set-api-key").value.trim();
  if (key) body.api_key = key;

  try {
    const resp = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      showBanner("settings-err", data.detail || "Kaydetme hatası");
      return;
    }
    showBanner("settings-ok", "Ayarlar kaydedildi.", true);
    document.getElementById("set-api-key").value = "";
    loadSettings();
  } catch (e) {
    showBanner("settings-err", `Bağlantı hatası: ${e.message}`);
  }
}

async function onTest() {
  const result = document.getElementById("test-result");
  if (result) result.textContent = "Test ediliyor…";

  const body = {
    base_url: normalizeBaseUrl(document.getElementById("set-base-url").value),
  };
  const key = document.getElementById("set-api-key").value.trim();
  if (key) body.api_key = key;

  try {
    const resp = await fetch("/api/settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.ok) {
      const models = (data.models || []).join(", ") || "—";
      showBanner("settings-ok", `Bağlantı başarılı. Modeller: ${models}`, true);
      if (result) result.textContent = `Base URL: ${data.base_url}`;
    } else {
      showBanner("settings-err", data.error || "Bağlantı başarısız");
      if (result) result.textContent = "";
    }
  } catch (e) {
    showBanner("settings-err", `Test hatası: ${e.message}`);
    if (result) result.textContent = "";
  }
}
