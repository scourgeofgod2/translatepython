/* mirapdf — Alpine.js app component */

function normalizeBaseUrl(url) {
  url = (url || '').trim().replace(/\/+$/, '');
  if (!url) return 'https://app.claude.gg/v1';
  if (!url.endsWith('/v1')) url += '/v1';
  return url;
}

const STATUS_LABEL = {
  queued: 'Sırada',
  running: 'Çeviriliyor',
  done: 'Tamamlandı',
  failed: 'Başarısız',
  canceled: 'İptal',
};

const STAGE_LABEL = {
  queued: 'Sırada',
  loading_model: 'Model yükleniyor',
  translating: 'Çeviriliyor',
  writing_pdf: 'PDF yazılıyor',
  finished: 'Bitti',
  failed: 'Hata',
  canceled: 'İptal edildi',
};

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // --- tab state ---
    tab: 'translate',

    // --- upload state ---
    selectedFile: null,
    fileLabel: '',
    isDragging: false,
    uploading: false,

    // --- translate form ---
    langIn: 'en',
    langOut: 'tr',
    pages: '',
    threads: 4,
    model: 'claude-sonnet-4-6',
    promptOverride: '',
    ignoreCache: false,

    // --- banners ---
    translateError: '',
    translateInfo: '',
    settingsOk: '',
    settingsErr: '',
    testResult: '',

    // --- jobs ---
    jobs: [],
    logs: {},

    // --- settings form ---
    baseUrl: '',
    apiKey: '',
    apiKeyStatus: 'Kayıtlı anahtar yok',
    settingsModel: 'claude-sonnet-4-6',
    settingsThreads: 4,
    settingsLangIn: 'en',
    settingsLangOut: 'tr',

    // --- computed ---
    get normalizedBaseUrl() {
      return normalizeBaseUrl(this.baseUrl);
    },

    // --- lifecycle ---
    init() {
      this.loadSettings();
      this.refreshJobs();
      this.startPolling();
    },

    // --- helpers ---
    statusLabel(status) {
      return STATUS_LABEL[status] || status;
    },
    stageLabel(stage) {
      return STAGE_LABEL[stage] || stage || '';
    },
    formatDate(dateStr) {
      return dateStr ? new Date(dateStr).toLocaleString('tr-TR') : '';
    },

    // --- upload ---
    setFile(f) {
      if (!f) return;
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        this.translateError = 'Sadece PDF dosyaları destekleniyor.';
        this.translateInfo = '';
        return;
      }
      if (f.size > 80 * 1024 * 1024) {
        this.translateError = 'Dosya çok büyük (maks 80 MB).';
        this.translateInfo = '';
        return;
      }
      this.translateError = '';
      this.selectedFile = f;
      this.fileLabel = `${f.name} · ${(f.size / 1024 / 1024).toFixed(1)} MB`;
    },

    async submitJob() {
      if (!this.selectedFile) return;
      this.translateError = '';
      this.translateInfo = '';
      this.uploading = true;

      const formData = new FormData();
      formData.append('file', this.selectedFile);
      formData.append('lang_in', this.langIn);
      formData.append('lang_out', this.langOut);
      formData.append('pages', this.pages);
      formData.append('threads', this.threads || 4);
      formData.append('model', this.model);
      formData.append('prompt_override', this.promptOverride);
      formData.append('ignore_cache', this.ignoreCache ? 'true' : 'false');

      try {
        const resp = await fetch('/api/jobs', { method: 'POST', body: formData });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          const detail = data.detail || `Hata ${resp.status}`;
          this.translateError = typeof detail === 'string' ? detail : JSON.stringify(detail);
          if (resp.status === 400 && String(detail).includes('API')) {
            this.tab = 'settings';
            this.loadSettings();
          }
          return;
        }
        this.selectedFile = null;
        this.fileLabel = '';
        this.translateInfo = 'İş oluşturuldu. İlerlemeyi İşler sekmesinden izleyin.';
        this.tab = 'jobs';
        this.refreshJobs();
      } catch (e) {
        this.translateError = `Bağlantı hatası: ${e.message}`;
      } finally {
        this.uploading = false;
      }
    },

    // --- jobs ---
    async refreshJobs() {
      try {
        const resp = await fetch('/api/jobs');
        if (!resp.ok) return;
        this.jobs = await resp.json();
      } catch {
        /* ignore network blips */
      }
    },

    startPolling() {
      setInterval(() => {
        if (this.tab === 'jobs') this.refreshJobs();
      }, 2000);
    },

    async deleteJob(id) {
      if (!confirm('Bu işi silmek istediğinize emin misiniz?')) return;
      await fetch(`/api/jobs/${id}`, { method: 'DELETE' });
      this.refreshJobs();
    },

    async toggleLog(id) {
      if (this.logs[id]) {
        delete this.logs[id];
        return;
      }
      const resp = await fetch(`/api/jobs/${id}/log`);
      this.logs[id] = await resp.text();
    },

    // --- settings ---
    async loadSettings() {
      try {
        const resp = await fetch('/api/settings');
        if (!resp.ok) return;
        const s = await resp.json();
        this.baseUrl = s.base_url || '';
        this.settingsModel = s.model || 'claude-sonnet-4-6';
        this.settingsThreads = s.threads || 4;
        this.settingsLangIn = s.lang_in || 'en';
        this.settingsLangOut = s.lang_out || 'tr';
        this.apiKeyStatus = s.api_key_set
          ? 'Kayıtlı anahtar mevcut (değiştirmek için yeni değer girin)'
          : 'Kayıtlı anahtar yok';
        if (s.api_key_set) {
          // placeholder handled via x-model binding
        }
      } catch {
        /* ignore */
      }
    },

    async saveSettings() {
      this.settingsOk = '';
      this.settingsErr = '';

      const body = {
        base_url: normalizeBaseUrl(this.baseUrl),
        model: this.settingsModel,
        threads: this.settingsThreads || 4,
        lang_in: this.settingsLangIn || 'en',
        lang_out: this.settingsLangOut || 'tr',
      };
      if (this.apiKey.trim()) body.api_key = this.apiKey.trim();

      try {
        const resp = await fetch('/api/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          this.settingsErr = data.detail || 'Kaydetme hatası';
          return;
        }
        this.settingsOk = 'Ayarlar kaydedildi.';
        this.apiKey = '';
        this.loadSettings();
      } catch (e) {
        this.settingsErr = `Bağlantı hatası: ${e.message}`;
      }
    },

    async testConnection() {
      this.testResult = 'Test ediliyor…';
      this.settingsOk = '';
      this.settingsErr = '';

      const body = {
        base_url: normalizeBaseUrl(this.baseUrl),
      };
      if (this.apiKey.trim()) body.api_key = this.apiKey.trim();

      try {
        const resp = await fetch('/api/settings/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (data.ok) {
          const models = (data.models || []).join(', ') || '—';
          this.settingsOk = `Bağlantı başarılı. Modeller: ${models}`;
          this.testResult = `Base URL: ${data.base_url}`;
        } else {
          this.settingsErr = data.error || 'Bağlantı başarısız';
          this.testResult = '';
        }
      } catch (e) {
        this.settingsErr = `Test hatası: ${e.message}`;
        this.testResult = '';
      }
    },
  }));
});
