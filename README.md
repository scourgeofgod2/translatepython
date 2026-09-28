# mirapdf

EN→TR (ve tersi) **düzen korunmuş PDF çeviri** web uygulaması.
Karmaşık düzenli bilimsel PDF'lerde formül, tablo ve çok sütunlu yerleşimi bozmadan çeviri yapar.

## Özellikler

- **pdf2zh** motoru (PDFMathTranslate, EMNLP 2025) ile kanıtlanmış düzen koruma
- OpenAI-uyumlu LLM API (varsayılan: `https://app.claude.gg`)
- Türkçe web arayüzü: sürükle-bırak yükleme, ilerleme takibi, tek tıkla indirme
- Mono Türkçe PDF çıktı
- Yerel iş kuyruğu (aynı anda 1 iş), sayfa aralığı, özel prompt

## Kurulum

```powershell
# uv + Python 3.12
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv python install 3.12

# Bağımlılıklar
uv sync --system-certs --extra dev

# data/.env içine API anahtarını koy
copy .env.example data\.env
# data\.env → OPENAI_API_KEY=...
```

> Kurumsal ağda TLS sertifikası sorunu varsa `--system-certs` ve
> `backend/app/ssl_boot` otomatik olarak sistem güven deposunu kullanır.

### Model / font indirme

pdf2zh ilk çalıştırmada gerekli model ve fontları otomatik indirir.

## Çalıştırma

```powershell
.\scripts\run.ps1
# → http://127.0.0.1:8765/
```

1. **Ayarlar** → API anahtarı + **Bağlantıyı Test Et**
2. **Çeviri** → PDF yükle → **Çeviriyi Başlat**
3. **İşler** → ilerleme → **İndir (PDF)**

## CLI ile doğrudan çevirme

```powershell
.\scripts\smoke_translate.ps1 path\to\file.pdf
```

## Test

```powershell
uv run --system-certs python -m pytest tests/ -q
```

## Mimari

```
backend/app/          FastAPI (jobs, settings, pdf2zh_runner)
frontend/             Vanilla JS UI (Çeviri / İşler / Ayarlar)
prompts/              EN→TR bilimsel çeviri promptu
scripts/              setup / run / smoke
data/                 .env + job artifacts (gitignored)
```

## Lisans

pdf2zh bileşeni AGPL-3.0 (Byaidu/PDFMathTranslate).
