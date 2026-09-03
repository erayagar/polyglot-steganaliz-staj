# Polyglot / Steganaliz Servisi

X (Twitter) gibi platformlarda paylaşılan görsel dosyaların arkasına gizlenmiş video/veri (polyglot dosya) tespiti yapan, uçtan uca bir siber güvenlik + bilgisayar görüsü + web servisi projesi.

Bu proje bir **20 günlük staj programı** kapsamında geliştirilmektedir. Günlük plan ve ilerleme takibi için: [PLAN.md](./PLAN.md)

> Bu proje yalnızca eğitim ve savunma (defensive security) amaçlıdır. Gerçek kullanıcı verisi toplanmaz veya kazınmaz (scraping yok); tüm test dosyaları bu proje kapsamında sentetik olarak üretilir.

## Durum

**Gün 14 / 20 tamamlandı** (Hafta 1-2: dosya format analizi + steganaliz motoru ✅, Hafta 3: FastAPI servisi 🔶 devam ediyor). Detaylı ilerleme ve kabul kriterleri için [PLAN.md](./PLAN.md); her günün "neden bu şekilde yapıldığı" açıklamaları için `docs/gunN-*.md` raporlarına bakın.

| Bileşen | Durum |
|---|---|
| Format analizi ve polyglot üretici (`scripts/`) | ✅ Hazır |
| Steganaliz motoru (trailer, entropy, boyut sapması, LSB/DCT, extraction) | ✅ Hazır |
| FastAPI backend (`backend/`) | 🔶 Çalışıyor, hata yönetimi (Gün 15) devam ediyor |
| Web arayüzü (`frontend/`) | ⬜ Henüz başlamadı (Gün 16-17) |

## Nasıl Çalışır

1. **Tespit** — Görselin gerçek dosya sonu (PNG `IEND`, JPEG `EOI`) baytlarından sonra kalan "trailer" veri taranır; içinde bilinen bir video/konteyner imzası (`ftyp`, `moov`, RIFF, EBML/WebM) aranır. Bu, ana tespit sinyalidir.
2. **Doğrulama** — Trailer sinyali; Shannon entropy'deki görsel/video geçiş sıçraması ve gerçek dosya boyutunun görsel çözünürlüğünden beklenen teorik boyuttan sapmasıyla desteklenir. Üç sinyal ağırlıklı olarak birleştirilip 0-100 arası bir `threat_score`e dönüştürülür.
3. **Ayıklama (extraction)** — Dosya polyglot ise, trailer'ın başlangıç offset'inden bölünüp gizli video bağımsız bir `.mp4` dosyası olarak kaydedilir ve API üzerinden oynatılabilir hale getirilir.

## Teknoloji Yığını
- **Backend:** Python 3.11+, FastAPI, Pydantic, Uvicorn
- **Görüntü/Video İşleme:** OpenCV, Pillow, NumPy, ffmpeg/ffprobe
- **Frontend:** HTML5 / CSS3 / Vanilla JS (Gün 16-17'de eklenecek)
- **Analiz:** Shannon entropy, LSB/DCT gürültü analizi, dosya trailer (EOF ötesi) taraması, teorik/gerçek boyut sapma analizi

## Proje Yapısı
```
polyglot-steganaliz-staj/
├── PLAN.md              # 20 günlük detaylı çalışma planı ve ilerleme takibi
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI uygulaması, /api/v1/analyze endpoint'i
│   │   ├── pipeline.py  # scripts/ analiz modüllerini API'ye bağlayan katman
│   │   └── models.py    # Pydantic yanıt modelleri (AnalyzeResponse, HealthResponse)
│   └── requirements.txt
├── frontend/             # Web dashboard (henüz boş, Gün 16-17)
├── scripts/              # Bağımsız çalıştırılabilir CLI analiz/üretim script'leri
├── samples/              # Sentetik test dosyaları (git'e dahil değil)
└── docs/                 # Format notları, test sonuçları, günlük raporlar (.md + .pdf)
```

## Kurulum

Proje kökünde tek bir sanal ortam (`.venv`) hem `scripts/`'i hem `backend/`'i
çalıştırmak için yeterlidir (ikisi de aynı `requirements.txt`'i kullanır):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Ayrıca video meta verisi analizi için `ffmpeg`/`ffprobe` kurulu olmalı (opsiyonel; kurulu değilse OpenCV'ye düşer):

```bash
brew install ffmpeg
```

## Kullanım

### API'yi çalıştırma

```bash
cd backend
source ../.venv/bin/activate
uvicorn app.main:app --reload
```

Servis `http://127.0.0.1:8000` üzerinde ayağa kalkar. İnteraktif dokümantasyon için `http://127.0.0.1:8000/docs` (Swagger UI).

### Bir dosyayı analiz etme

```bash
curl -F "file=@samples/polyglot_png.png;type=image/png" \
  http://127.0.0.1:8000/api/v1/analyze
```

Örnek yanıt (`AnalyzeResponse`):

```json
{
  "polyglot_status": true,
  "threat_score": 76,
  "extracted_video_url": "/media/81c78d83ac5d4b9289d8bafbf44fdf7f_extracted.mp4",
  "analysis_summary": "Görsele gizlenmiş video tespit edildi: 'mp4/ftyp' imzası offset 217 konumunda bulundu (threat_score=76). Ayıklanan video: 64x64, 2.0 sn, codec=h264."
}
```

`extracted_video_url` doluysa, ayıklanan video `http://127.0.0.1:8000<extracted_video_url>` adresinden doğrudan oynatılabilir/indirilebilir.

Yalnızca PNG/JPEG kabul edilir (magic bytes ile doğrulanır) ve dosya boyutu 25 MB ile sınırlıdır; bu kısıtların dışına çıkan istekler anlamlı bir `4xx` hata mesajıyla reddedilir.

### CLI script'leri (analiz motorunun temeli)

`backend/`, aslında bu script'leri sarmalayan bir API katmanıdır — her biri
tek başına, dosya vermeden de kullanılabilir:

```bash
# Sentetik polyglot dosya üretimi (görsel + video birleştirme)
python scripts/make_polyglot.py --image samples/sample.png --video samples/sample.mp4 --output samples/polyglot.png

# Tek komutla tam analiz (trailer + boyut sapması + entropy)
python scripts/analyze.py --file samples/polyglot.png --json

# Gizli videoyu bağımsız dosya olarak ayıklama
python scripts/extract.py --file samples/polyglot.png --output-dir samples/extracted

# Ayıklanan videonun meta verisi (kare sayısı, süre, codec)
python scripts/video_metadata.py --file samples/extracted/polyglot_extracted.mp4
```

Her script'in kendi `--help` çıktısı ve `docs/gunN-*.md` raporlarında ayrıntılı gerekçesi mevcuttur.

## Dokümantasyon

- [`PLAN.md`](./PLAN.md) — 20 günlük plan, kabul kriterleri, ilerleme durumu
- [`docs/format-notlari.md`](./docs/format-notlari.md) — PNG/JPEG/MP4 binary format notları
- [`docs/test-sonuclari.md`](./docs/test-sonuclari.md) — farklı senaryolarda tespit başarımı
- `docs/gunN-*.md` / `.pdf` — her günün hedefi, yaklaşımı, test sonuçları ve notları

## Lisans / Etik Not
Bu proje yalnızca eğitim ve savunma amaçlı geliştirilmiştir. Herhangi bir platformdan izinsiz veri kazıma (scraping) veya gerçek kullanıcı verisiyle test yapılmaz; tüm örnek dosyalar sentetik olarak üretilir.
