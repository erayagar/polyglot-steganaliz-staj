# Polyglot / Steganaliz Servisi

X (Twitter) gibi platformlarda paylaşılan görsel dosyaların arkasına gizlenmiş video/veri (polyglot dosya) tespiti yapan, uçtan uca bir siber güvenlik + bilgisayar görüsü + web servisi projesi.

Bu proje bir **20 günlük staj programı** kapsamında geliştirildi. Günlük plan ve ilerleme takibi için: [PLAN.md](./PLAN.md)

> Bu proje yalnızca eğitim ve savunma (defensive security) amaçlıdır. Gerçek kullanıcı verisi toplanmaz veya kazınmaz (scraping yok); tüm test dosyaları bu proje kapsamında sentetik olarak üretilir.

## Durum

**Gün 20 / 20 tamamlandı — proje bitti.** Plan tamamlandıktan sonra
yapılan kod incelemesinde (2026-10-23) bulunan hatalar düzeltildi ve otomatik
bir test paketi eklendi (ayrıntı: [`docs/test-sonuclari.md`](./docs/test-sonuclari.md)
son bölüm).

Detaylı ilerleme ve kabul kriterleri için [PLAN.md](./PLAN.md); her günün "neden bu şekilde yapıldığı" açıklamaları için `docs/gunN-*.md` raporlarına (indeks: [`docs/README.md`](./docs/README.md)) bakın; genel özet için [`docs/staj-raporu.md`](./docs/staj-raporu.md).

| Bileşen | Durum |
|---|---|
| Format analizi ve polyglot üretici (`scripts/`) | ✅ Hazır |
| Steganaliz motoru (trailer + konteyner doğrulama, entropy, boyut sapması, extraction) | ✅ Hazır |
| LSB/DCT analizi (`scripts/lsb_analysis.py`, `scripts/dct_analysis.py`) | 🧪 Yalnızca CLI, deneysel/tamamlayıcı — API skoruna dahil değil |
| FastAPI backend (`backend/`) | ✅ Hazır |
| Web arayüzü (`frontend/`, backend'e canlı bağlı) | ✅ Hazır, uçtan uca doğrulandı (12/12 test dosyası doğru sınıflandı) |
| Otomatik testler (`tests/`, `pytest`) | ✅ 40 test |
| Dokümantasyon (README, docstring'ler, `docs/` indeksi) | ✅ Hazır |

## Nasıl Çalışır

1. **Tespit** — Görselin gerçek dosya sonu (PNG `IEND`, JPEG `EOI`) baytlarından sonra kalan "trailer" veri taranır; içinde bilinen bir video/konteyner imzası (`ftyp`/`moov`/`mdat`, RIFF/AVI, EBML/WebM) aranır. Bulunan her aday **konteyner yapısına göre doğrulanır** (ISO-BMFF box zinciri, `RIFF....AVI ` formu, EBML DocType `webm`/`matroska`); böylece trailer'daki düz metinde geçen "moov" gibi kelimeler yanlış pozitif üretmez. Bu, ana tespit sinyalidir.
2. **Doğrulama** — Trailer sinyali; Shannon entropy'deki görsel/trailer geçiş sıçraması ve gerçek dosya boyutunun görsel çözünürlüğünden beklenen teorik boyuttan sapmasıyla desteklenir. Video imzası taşımayan ama eşik üstü (≥16 bayt) EOF sonrası veri de (ör. arkaya eklenmiş ZIP/RAR/7z/PDF) şüpheli kabul edilir. Sinyaller ağırlıklı olarak birleştirilip 0-100 arası bir `threat_score`e dönüştürülür (bkz. [Tehdit skoru](#tehdit-skoru)).
3. **Ayıklama (extraction)** — Dosya polyglot ise, tespit edilen video konteynerinin başlangıç offset'inden bölünür (görselle video arasındaki ara veri atlanır) ve gizli video imzasına uygun uzantıyla (`.mp4`/`.avi`/`.webm`) bağımsız bir dosya olarak kaydedilip API üzerinden oynatılabilir hale getirilir.

### Tehdit skoru

`backend/app/pipeline.py` → `compute_threat_score`:

| Sinyal | Katkı | Koşul |
|---|---|---|
| Doğrulanmış video imzası (polyglot) | 60 | trailer'da geçerli video konteyneri var |
| İmzası tanınmayan trailer | 35 | video yok ama EOF sonrası ≥16 bayt veri var (yukarıdakiyle birlikte sayılmaz) |
| Entropy farkı | 0-25 | sınır öncesi/sonrası ortalama entropy farkı; 3.0 bit/bayt'ta tam puan |
| Boyut sapması | 0-15 | yalnızca EOF sonrası veri varken; teorik boyutun %100 üstünde tam puan |

Boyut sapması tek başına güvenilir değildir (sabit sıkıştırma oranı
varsayımı temiz görsellerde de yüksek sapma üretebilir), bu yüzden yalnızca
destekleyici sinyal olarak kullanılır. Arayüz skoru 0-33 düşük, 34-66 orta,
67-100 yüksek olarak renklendirir.

### Mimari / İstek Akışı

```
Tarayıcı (frontend/app.js)
   │  fetch POST, multipart/form-data
   ▼
FastAPI /api/v1/analyze (backend/app/main.py)
   │  Content-Length > 25 MB ise gövde okunmadan 413
   │  format magic bytes'tan belirlenir, dosya backend/tmp/ altına kaydedilir
   │  asyncio.to_thread(...)  — CPU-yoğun analiz event loop'u bloklamasın diye ayrı thread'de çalışır
   ▼
pipeline.run_pipeline (backend/app/pipeline.py)
   │  dosyayı bir kez okuyup scripts/ modüllerine bellekteki baytları verir:
   │  detect_trailer.analyze_bytes → size_analysis.analyze_bytes → analyze.entropy_summary
   │  → (polyglot ise) extract.extract → video_metadata.get_metadata
   │  bittiğinde yüklenen dosya silinir, 1 saatten eski media/ dosyaları temizlenir
   ▼
pipeline.compute_threat_score + build_analysis_summary
   │  trailer/entropy/boyut sinyallerini 0-100 threat_score'a ağırlıklı birleştirir
   ▼
AnalyzeResponse (JSON) ──► frontend'de risk skoru/özet gösterimi
   └─ extracted_video_url ──► StaticFiles ("/media") ──► <video> player
```

`scripts/` altındaki modüller bağımsız CLI araçları olarak da (backend
olmadan) doğrudan çalıştırılabilir — `backend/` bunları HTTP üzerinden
sarmalayan ince bir katmandır.

## Teknoloji Yığını
- **Backend:** Python 3.11+, FastAPI, Pydantic, Uvicorn
- **Görüntü/Video İşleme:** OpenCV, Pillow, NumPy, Matplotlib, ffmpeg/ffprobe
- **Frontend:** HTML5 / CSS3 / Vanilla JS (sürükle-bırak yükleme, backend'e canlı `fetch` entegrasyonu)
- **Analiz:** dosya trailer (EOF ötesi) taraması ve konteyner yapısı doğrulaması, Shannon entropy, teorik/gerçek boyut sapma analizi; CLI'da deneysel LSB/DCT gürültü analizi
- **Test:** pytest, FastAPI `TestClient` (httpx2)

## Proje Yapısı
```
polyglot-steganaliz-staj/
├── PLAN.md               # 20 günlük detaylı çalışma planı ve ilerleme takibi
├── requirements-dev.txt  # backend gereksinimleri + pytest/httpx2
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI uygulaması, /api/v1/analyze endpoint'i, yükleme doğrulama/temizlik
│   │   ├── pipeline.py   # scripts/ analiz modüllerini API'ye bağlayan katman, threat_score
│   │   └── models.py     # Pydantic yanıt modelleri (AnalyzeResponse, HealthResponse)
│   └── requirements.txt
├── frontend/             # Web dashboard (sürükle-bırak yükleme, sonuç/video gösterimi)
├── scripts/              # Bağımsız çalıştırılabilir CLI analiz/üretim script'leri
├── samples/              # Küçük sentetik örnek dosyalar (testler kullanır; türetilen
│                         # samples/extracted/ ve samples/test_matrix/ git'e dahil değil)
├── tests/                # pytest test paketi (scripts/ + API)
└── docs/                 # Format notları, test sonuçları, günlük raporlar (.md + .pdf)
```

## Kurulum

Proje kökünde tek bir sanal ortam (`.venv`) hem `scripts/`'i hem `backend/`'i
çalıştırmak için yeterlidir (ikisi de aynı `backend/requirements.txt`'i kullanır):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt      # yalnızca çalıştırmak için
pip install -r requirements-dev.txt          # testleri de çalıştırmak için (yukarıdakini içerir)
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

### Web arayüzünü çalıştırma

Backend ayaktayken, `frontend/index.html` doğrudan tarayıcıda açılabilir
(`file://` ile) veya ayrı bir origin'den statik olarak sunulabilir:

```bash
cd frontend
python3 -m http.server 5500
```

Ardından `http://127.0.0.1:5500` adresi tarayıcıda açılır. Bir PNG/JPEG
sürükleyip bırakınca (veya tıklayıp seçince) dosya otomatik olarak backend'e
gönderilir; tehdit skoru, analiz özeti ve (varsa) ayıklanan videonun
oynatıcısı ekranda gösterilir. Backend `CORSMiddleware` ile farklı origin'den
gelen isteklere izin verecek şekilde yapılandırılmıştır.

Backend farklı bir adreste çalışıyorsa `frontend/index.html` içindeki
`<meta name="api-base-url" content="http://127.0.0.1:8000" />` değeri
değiştirilir.

### Bir dosyayı analiz etme

```bash
curl -F "file=@samples/polyglot_png.png" http://127.0.0.1:8000/api/v1/analyze
```

Örnek yanıt (`AnalyzeResponse`, HTTP `200`):

```json
{
  "polyglot_status": true,
  "threat_score": 75,
  "extracted_video_url": "/media/81c78d83ac5d4b9289d8bafbf44fdf7f_extracted.mp4",
  "analysis_summary": "Görsele gizlenmiş video tespit edildi: 'mp4/ftyp' imzası offset 217 konumunda bulundu (threat_score=75). Ayıklanan video: 64x64, 2.0 sn, codec=h264."
}
```

| Alan | Açıklama |
|---|---|
| `polyglot_status` | Trailer'da doğrulanmış bir video konteyneri bulunduysa `true` |
| `threat_score` | 0-100 ağırlıklı tehdit skoru (bkz. [Tehdit skoru](#tehdit-skoru)) |
| `extracted_video_url` | Ayıklanan videonun yolu; polyglot değilse `null`. `http://127.0.0.1:8000<url>` adresinden oynatılabilir/indirilebilir; 1 saat sonra silinir |
| `analysis_summary` | İnsan tarafından okunabilir özet (video çözünürlüğü/süresi/codec'i dahil) |

### Doğrulama ve hata kodları

| Durum | HTTP |
|---|---|
| Başarılı analiz | `200` |
| Boş dosya, PNG/JPEG olmayan içerik, beyan edilen PNG/JPEG tipiyle uyuşmayan içerik | `400` |
| 25 MB'ı aşan dosya (Content-Length varsa gövde okunmadan) | `413` |
| Bozuk/geçersiz görsel yapısı (IEND/EOI yok, geçersiz başlık vb.) | `422` |
| Beklenmeyen sunucu hatası (stack trace sızdırmadan) | `500` |

Format, client'ın beyan ettiği `Content-Type`'tan değil dosyanın magic
bytes'ından belirlenir; genel bir tip (ör. `application/octet-stream`)
gönderilse de geçerli bir PNG/JPEG kabul edilir. Yüklenen dosya analizden
sonra `backend/tmp/`'ten silinir.

### CLI script'leri (analiz motorunun temeli)

`backend/`, aslında bu script'leri sarmalayan bir API katmanıdır — her biri
backend olmadan, tek başına da kullanılabilir (komutlar proje kökünden
çalıştırılır):

```bash
# Sentetik polyglot dosya üretimi (görsel + video birleştirme)
python scripts/make_polyglot.py --image samples/sample.png --video samples/sample.mp4 --output samples/test_matrix/polyglot.png

# Gün 10 test matrisini (yeniden sıkıştırma senaryoları + temiz gradient) üretme
python scripts/make_test_scenarios.py

# Tek komutla tam analiz (trailer + boyut sapması + entropy)
python scripts/analyze.py --file samples/test_matrix/polyglot.png --json

# Tekil analizler
python scripts/detect_trailer.py --file samples/polyglot_png.png      # EOF sonrası trailer + imza doğrulama
python scripts/size_analysis.py --file samples/polyglot_jpg.jpg       # teorik/gerçek boyut sapması
python scripts/entropy.py --file samples/polyglot_png.png             # blok entropy grafiği (docs/entropy-*.png)

# Gizli videoyu bağımsız dosya olarak ayıklama (ara veri atlanır, uzantı imzaya göre seçilir)
python scripts/extract.py --file samples/test_matrix/polyglot.png --output-dir samples/extracted

# Ayıklanan videonun meta verisi (kare sayısı, süre, codec)
python scripts/video_metadata.py --file samples/extracted/polyglot_extracted.mp4

# Deneysel LSB/DCT analizleri (yalnızca CLI, API skoruna dahil değil)
python scripts/lsb_analysis.py --file samples/lsb_stego_sample.png
python scripts/dct_analysis.py --file samples/lsb_stego_sample.png
```

Her script'in kendi `--help` çıktısı ve `docs/gunN-*.md` raporlarında ayrıntılı gerekçesi mevcuttur.

## Testler

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

| Dosya | Kapsam |
|---|---|
| `tests/test_detect_trailer.py` | JPEG/PNG sonu tespiti (bozuk/kesik dosyalar, dolgu baytları), imza doğrulama ve yanlış pozitifler, ara veri/AVI/WebM ayıklama, ZIP trailer |
| `tests/test_size_analysis.py` | SOF/IHDR okuma, geçersiz kanal sayısı ve bit derinliği |
| `tests/test_scoring.py` | Örnek dosyaların `threat_score`'u (temiz → 0, polyglot ≥ 60, imzasız trailer orta düzey) |
| `tests/test_api.py` | `TestClient` ile `/api/v1/analyze`: 200/400/413/422, CORS, magic-byte format tespiti, geçici dosya temizliği |

## Bilinen Kısıtlar

- Tespit **trailer-append** tehdit modeline odaklanır; görselin *içine*
  gömülen veri (PNG ancillary chunk, JPEG APPn/COM segmenti) ve LSB
  steganografi API tarafından tespit edilmez.
- Tespit başarımı küçük, tamamen sentetik dosyalarla ölçülmüştür; gerçek
  fotoğraf boyutlarında ve gerçek encoder'larla üretilmiş AVI/WebM
  videolarla doğrulanmamıştır (bkz. [`docs/test-sonuclari.md`](./docs/test-sonuclari.md)).
- Content-Length göndermeyen (chunked) isteklerde 25 MB sınırı gövde
  okunurken uygulanır.
- CORS tüm origin'lere açıktır ve kimlik doğrulama yoktur — yalnızca
  yerel geliştirme/demo içindir.

## Dokümantasyon

- [`PLAN.md`](./PLAN.md) — 20 günlük plan, kabul kriterleri, ilerleme durumu
- [`docs/README.md`](./docs/README.md) — `docs/` klasörünün tam indeksi (tüm günlük/haftalık raporlar ve görseller kategorilere ayrılmış halde)
- [`docs/format-notlari.md`](./docs/format-notlari.md) — PNG/JPEG/MP4 binary format notları
- [`docs/test-sonuclari.md`](./docs/test-sonuclari.md) — farklı senaryolarda tespit başarımı ve kod incelemesi sonrası yeniden ölçüm
- [`docs/staj-raporu.md`](./docs/staj-raporu.md) — staj final raporu (özet, yöntem, karşılaşılan zorluklar, sonuçlar)
- `docs/gunN-*.md` / `.pdf` — her günün hedefi, yaklaşımı, test sonuçları ve notları

## Günlerin Ardından Geliştirmeler (Opsiyonel)

20 günlük planın parçası değildir. Proje işlevsel olarak tamamlandıktan
sonra, kapsamı genişletmeden eklenebilecek kalite/sunum iyileştirmeleri
[`PLAN.md`](./PLAN.md#günlerin-ardından-geliştirmeler-opsiyonel) içinde
ayrı bir başlık altında listelenmiştir (ör. arayüz ekran görüntüsü, görsel
mimari diyagramı). Otomatik `pytest` test paketi bu listeden tamamlandı.
Hiçbiri zorunlu değildir.

## Lisans / Etik Not
Bu proje yalnızca eğitim ve savunma amaçlı geliştirilmiştir. Herhangi bir platformdan izinsiz veri kazıma (scraping) veya gerçek kullanıcı verisiyle test yapılmaz; tüm örnek dosyalar sentetik olarak üretilir.
