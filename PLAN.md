# 20 Günlük Staj Programı: X (Twitter) Platformunda Görsel Arkasına Saklanmış Video ve Veri Tespiti (Polyglot / Steganaliz Servisi)

Bu proje; siber güvenlik (steganaliz / polyglot dosya analizi), bilgisayar görüsü (dosya ve piksel düzeyi anomali tespiti) ve web API / full-stack geliştirme yetkinliklerini veri kazıma (scraping) veya veri toplama yükü olmadan harmanlayan uçtan uca bir çalışmadır.

> **Kapsam notu:** Bu proje yalnızca eğitim ve savunma (defensive security) amaçlıdır. Gerçek kullanıcı verisi toplanmaz veya kazınmaz (scraping yok); tüm test dosyaları bu proje kapsamında sentetik olarak üretilir.

## Kullanılacak Teknolojiler
- **Dil:** Python 3.11+
- **Görüntü/Video İşleme:** OpenCV, Pillow, NumPy
- **Analiz Araçları:** ffmpeg / ffprobe, hex editor (`xxd`/`hexyl` veya GUI alternatifi)
- **Backend:** FastAPI, Pydantic, Uvicorn
- **Frontend:** HTML5 / CSS3 / Vanilla JS (sürükle-bırak yükleme, HTML5 `<video>` player)
- **Diğer:** matplotlib (entropy grafikleri)

## İlerleme Takibi
Her günün alt görevleri tamamlandıkça `- [ ]` kutucuklarını `- [x]` olarak işaretleyin.

---

## 1. Hafta: Dosya Format Mimarisi, Polyglot Oluşturma ve Header/EOF Analizi

### Gün 1 — Ortam Kurulumu ve Oryantasyon
**Hedef:** Geliştirme ortamının eksiksiz ve çalışır durumda kurulması.
**Alt Görevler:**
- [x] Python 3.11+ kurulumunun doğrulanması, proje için `.venv` sanal ortamının oluşturulması
- [x] `opencv-python`, `Pillow`, `fastapi`, `uvicorn`, `numpy`, `matplotlib`, `python-multipart` paketlerinin kurulması ve `backend/requirements.txt` içine yazılması
- [x] `ffmpeg`/`ffprobe` kurulumu (Homebrew: `brew install ffmpeg`) ve doğrulanması
- [x] Hex editor aracının kurulması (örn. `brew install hexyl` veya `xxd` kullanımı)
- [x] Proje klasör yapısının gözden geçirilmesi (`backend/`, `frontend/`, `scripts/`, `samples/`, `docs/`)
**Kabul Kriterleri:**
- `python -c "import cv2, PIL, fastapi, numpy, matplotlib"` hatasız çalışır
- `ffprobe -version` ve `ffmpeg -version` komutları sürüm bilgisi döner
- `hexyl` veya `xxd` ile örnek bir dosya hex formatında görüntülenebilir
**Notlar/Riskler:**
- macOS'ta OpenCV kurulumu bazen ek sistem bağımlılığı isteyebilir; sorun çıkarsa `opencv-python-headless` denenebilir.

---

### Gün 2 — Görsel ve Video Formatlarının Binary Düzeyde İncelenmesi
**Hedef:** PNG, JPEG ve MP4 formatlarının iç yapısını (chunk/marker/atom) somut örneklerle anlamak.
**Alt Görevler:**
- [x] Küçük bir PNG dosyasının hex dökümünde `IHDR`, `IDAT`, `IEND` chunk'larının bulunması
- [x] Küçük bir JPEG dosyasının hex dökümünde `SOI` (FFD8), `APPn`, `EOI` (FFD9) marker'larının bulunması
- [x] Küçük bir MP4 dosyasının hex dökümünde `ftyp`, `moov`, `mdat` atom'larının bulunması
- [x] `docs/format-notlari.md` dosyasının yazılması: her formatın imza baytları (magic bytes) ve sonlandırıcı işaretleri tablo halinde
**Kabul Kriterleri:**
- `docs/format-notlari.md` içinde PNG/JPEG/MP4 için en az imza (magic bytes) ve dosya sonu/işaret baytları tablosu mevcut
- Örnek bir PNG ve JPEG dosyasında IEND/EOI konumu hex offset olarak not edilmiş
**Notlar/Riskler:**
- MP4 dosyalarında atom sırası (`ftyp` önce, `moov`/`mdat` sırası değişken) farklı encoder'lara göre değişebilir; bu değişkenlik not edilmeli.

---

### Gün 3 — Sentetik Polyglot (Resim+Video) Üretici Script
**Hedef:** Meşru bir görselin arkasına MP4 videosu ekleyen bir Python script'i yazmak.
**Alt Görevler:**
- [x] `scripts/make_polyglot.py` dosyasının oluşturulması: `image_path`, `video_path`, `output_path` parametreleri alan CLI script
- [x] Görsel dosyasının ham baytlarının okunup, MP4 dosyasının baytlarının doğrudan arkasına eklenmesi (basit concatenation)
- [x] Üretilen dosyanın `samples/` altına örnek olarak kaydedilmesi (`.gitignore` ile git'e dahil edilmeyecek)
- [x] Script'in hem PNG+MP4 hem JPEG+MP4 kombinasyonlarını desteklemesi
**Kabul Kriterleri:**
- Üretilen polyglot dosya bir görsel görüntüleyicide (Preview, tarayıcı vb.) sorunsuz açılıyor
- Üretilen dosyanın boyutu ≈ orijinal görsel boyutu + orijinal video boyutu (küçük header farkları hariç)
- `file <output>` komutu dosyayı görsel formatı olarak tanıyor
**Notlar/Riskler:**
- Bazı görsel görüntüleyiciler/tarayıcılar EXIF/metadata doğrulaması yaparken hataya düşebilir; test için birden fazla görüntüleyici denenmeli.

---

### Gün 4 — EOF Ötesi Bayt Tarama ve Video Header Tespiti
**Hedef:** Dosya sonu (EOF) işaretinden sonra kalan trailer baytlarını tarayıp gizli video header imzalarını bulan algoritmayı geliştirmek.
**Alt Görevler:**
- [x] `scripts/detect_trailer.py` dosyasının oluşturulması
- [x] Görsel formatına göre EOF işaretinin (PNG: `IEND` + CRC, JPEG: `FFD9`) bulunması
- [x] EOF sonrası kalan baytlarda bilinen video imzalarının (`ftyp`, `moov`, RIFF/AVI gibi) aranması
- [x] Bulunan offset, imza türü ve trailer boyutunun konsola/JSON olarak raporlanması
**Kabul Kriterleri:**
- Gün 3'te üretilen polyglot dosyada gizli video başlangıç offset'i doğru tespit ediliyor
- Trailer içermeyen temiz bir görselde script "polyglot değil" sonucunu doğru veriyor (false-positive yok)
**Notlar/Riskler:**
- JPEG'lerde bazı uygulamalar EOI sonrasına zararsız metadata/padding ekleyebilir; bu durumun "gerçek video" ile karıştırılmaması için minimum imza uzunluğu/boyut eşiği kullanılmalı.

---

### Gün 5 — Shannon Entropy Analizi ve Görselleştirme
**Hedef:** Dosya içindeki veri yoğunluğu farklarını entropy hesabıyla ortaya çıkarmak.
**Alt Görevler:**
- [x] `scripts/entropy.py` dosyasının oluşturulması: dosyayı sabit boyutlu bloklara bölüp her blok için Shannon entropy hesaplayan fonksiyon
- [x] matplotlib ile blok bazlı entropy değerlerinin çizgi/bar grafiği olarak görselleştirilmesi
- [x] Polyglot dosyada görsel bölgesi ile video bölgesi arasındaki entropy farkının grafikte görünür olması
**Kabul Kriterleri:**
- Üretilen entropy grafiğinde görsel/video geçiş noktası görsel olarak ayırt edilebiliyor
- Grafik `docs/` veya `samples/` altına PNG olarak kaydedilebiliyor
**Notlar/Riskler:**
- Sıkıştırılmış görseller (JPEG) zaten yüksek entropy'ye sahip olduğundan görsel/video ayrımı PNG'lere göre daha zor olabilir; bu fark rapor edilmeli.

**Hafta 1 Çıktısı:** Gönderilen dosyadaki gizli video başlıklarını tespit eden çalışan Python analiz modülü (`scripts/detect_trailer.py` + `scripts/entropy.py`), CLI'dan çalıştırılabilir durumda.

---

## 2. Hafta: Görüntü İşleme, Steganaliz ve Gizli Medya Ayıklama (Extraction)

### Gün 6 — Teorik vs Gerçek Dosya Boyutu Sapma Analizi
**Hedef:** Görsel çözünürlüğü ve renk derinliğinden beklenen teorik dosya boyutunu hesaplayıp gerçek boyutla karşılaştırmak.
**Alt Görevler:**
- [x] `scripts/size_analysis.py` dosyasının oluşturulması
- [x] Görsel formatına göre (sıkıştırmasız PNG için piksel×renk derinliği, JPEG için ortalama sıkıştırma oranı tahmini) teorik boyut hesabı
- [x] Teorik boyut ile gerçek dosya boyutu arasındaki sapma yüzdesinin hesaplanması
- [x] Sapma oranı bir eşik değeri (örn. %20+) aşarsa "şüpheli" olarak işaretlenmesi
**Kabul Kriterleri:**
- Polyglot dosyalarda sapma oranı belirgin şekilde yüksek çıkıyor
- Temiz dosyalarda sapma oranı düşük/normal aralıkta kalıyor
**Notlar/Riskler:**
- JPEG sıkıştırma oranı içerik türüne (detay yoğunluğu) göre değişken olduğundan bu yöntem tek başına değil, diğer sinyallerle (entropy, trailer tespiti) birlikte kullanılmalı.

---

### Gün 7 — LSB ve DCT Frekans Alanı Gürültü Analizi
**Hedef:** OpenCV ile görsel üzerinde LSB steganografi izlerini ve DCT tabanlı frekans anomalilerini incelemek.
**Alt Görevler:**
- [x] `scripts/lsb_analysis.py`: görselin en az anlamlı bitlerini (LSB) çıkarıp görselleştiren fonksiyon
- [x] `scripts/dct_analysis.py`: OpenCV `cv2.dct` ile blok bazlı DCT katsayılarının hesaplanması ve anormal yüksek frekans bileşenlerinin görselleştirilmesi
- [x] İki analiz çıktısının karşılaştırmalı olarak `docs/` altına örnek görsellerle kaydedilmesi
**Kabul Kriterleri:**
- LSB görselleştirmesinde manipüle edilmiş/polyglot bir dosya ile temiz bir dosya arasında görsel fark ayırt edilebiliyor
- DCT analizi çalışıyor ve blok bazlı katsayı haritası üretebiliyor
**Notlar/Riskler:**
- Bu projenin ana tehdit modeli LSB steganografi değil, trailer-append polyglot olduğundan; LSB/DCT analizleri tamamlayıcı sinyal olarak konumlandırılmalı, ana tespit mekanizması olarak sunulmamalı.

---

### Gün 8 — Extraction (Unpolyglot) Fonksiyonu
**Hedef:** Görsel arkasına gizlenmiş MP4 video akışını orijinal görselden ayırıp bağımsız dosya olarak kaydetmek.
**Alt Görevler:**
- [x] `scripts/extract.py` dosyasının oluşturulması
- [x] Gün 4'teki `detect_trailer.py` çıktısını (offset bilgisi) kullanarak dosyanın ikiye bölünmesi: temiz görsel kısmı ve video kısmı
- [x] Ayıklanan video kısmının `.mp4` uzantısıyla `samples/extracted/` altına kaydedilmesi
- [x] Ayıklanan görsel kısmının da (opsiyonel) orijinal görsel olarak doğrulanması
**Kabul Kriterleri:**
- Ayıklanan `.mp4` dosyası `ffprobe` ile hatasız açılıyor ve bir video player'da oynatılabiliyor
- Ayıklama işlemi sonrası orijinal polyglot dosyanın boyutu = ayıklanan görsel boyutu + ayıklanan video boyutu
**Notlar/Riskler:**
- Yok.

---

### Gün 9 — Ayıklanan Video Meta Verisi Analizi
**Hedef:** Ayıklanan gizli videonun kare sayısı, süresi, çözünürlüğü ve codec bilgisinin çıkarılması.
**Alt Görevler:**
- [x] `scripts/video_metadata.py`: `ffprobe -print_format json` çıktısını parse eden fonksiyon
- [x] OpenCV `cv2.VideoCapture` ile alternatif/yedek bir kare sayısı ve FPS okuma yöntemi
- [x] Sonuçların yapılandırılmış (dict/JSON) formatta döndürülmesi
**Kabul Kriterleri:**
- Ayıklanan örnek videolar için kare sayısı, süre (saniye), çözünürlük ve codec adı doğru şekilde raporlanıyor
**Notlar/Riskler:**
- Yok.

---

### Gün 10 — Farklı Senaryolarda Tespit Başarımının Ölçülmesi
**Hedef:** Görsel sıkıştırma ve farklı format kombinasyonlarında sistemin tespit başarımını test etmek.
**Alt Görevler:**
- [x] En az 4 farklı test senaryosu üretilmesi: (1) PNG+MP4 polyglot, (2) JPEG+MP4 polyglot, (3) yeniden sıkıştırılmış/optimize edilmiş polyglot, (4) temiz (video içermeyen) görseller
- [x] Her senaryo için pipeline'ın (`detect_trailer` + `entropy` + `size_analysis`) çalıştırılıp sonuçların tablo halinde `docs/test-sonuclari.md` içine yazılması
- [x] Yanlış pozitif / yanlış negatif oranlarının not edilmesi
**Kabul Kriterleri:**
- `docs/test-sonuclari.md` en az 4 senaryo için sonuç satırı içeriyor
- Sistem temiz dosyalarda %0'a yakın false-positive veriyor
**Notlar/Riskler:**
- Görsel optimizasyon araçları (örn. PNG yeniden sıkıştırma) bazen trailer verisini bozabilir; bu sınır durum ayrıca not edilmeli.

**Hafta 2 Çıktısı:** Resim arkasındaki gizli videoyu ayıran ve bağımsız `.mp4` dosyası olarak kaydeden Steganaliz Motoru (`scripts/extract.py` + destekleyici modüller), tek bir `scripts/analyze.py` pipeline'ında birleştirilmiş.

---

## 3. Hafta: Web API (FastAPI) ve Arka Plan Servis Mimarisi

### Gün 11 — FastAPI Proje İskeleti ve Pydantic Modelleri
**Hedef:** Backend servisinin temel iskeletini kurmak.
**Alt Görevler:**
- [x] `backend/app/main.py` içinde FastAPI uygulamasının oluşturulması
- [x] `backend/app/models.py` içinde Pydantic response modelinin (`AnalyzeResponse`) tanımlanması
- [x] `backend/requirements.txt` dosyasının güncellenmesi (fastapi, uvicorn, python-multipart, opencv-python, pillow, numpy)
- [x] `uvicorn app.main:app --reload` ile servisin ayağa kalktığının doğrulanması
**Kabul Kriterleri:**
- `uvicorn` ile başlatılan servis `http://127.0.0.1:8000` üzerinde `{"status": "ok"}` benzeri bir health-check endpoint'i döndürüyor
**Notlar/Riskler:**
- Yok.

---

### Gün 12 — Dosya Yükleme Endpoint'i
**Hedef:** Kullanıcının şüpheli görsel yükleyebileceği endpoint'i yazmak.
**Alt Görevler:**
- [x] `POST /api/v1/analyze` endpoint'inin `UploadFile` parametresiyle tanımlanması
- [x] Yüklenen dosyanın geçici bir dizine (`backend/tmp/` veya benzeri, `.gitignore`'da) kaydedilmesi
- [x] Dosya boyutu ve MIME type doğrulaması (yalnızca PNG/JPEG kabul edilmesi)
**Kabul Kriterleri:**
- Swagger UI (`/docs`) üzerinden bir görsel dosyası yüklenip başarıyla kabul ediliyor
- Desteklenmeyen bir dosya türü (örn. `.txt`) yüklendiğinde uygun hata dönüyor
**Notlar/Riskler:**
- Yok.

---

### Gün 13 — Pipeline'ın FastAPI'ye Asenkron Entegrasyonu
**Hedef:** 1-2. haftada yazılan analiz/extraction pipeline'ını API'ye bağlamak.
**Alt Görevler:**
- [x] `scripts/` altındaki modüllerin `backend/app/pipeline.py` içinden import edilebilir hale getirilmesi (gerekirse `scripts/` bir Python paketine dönüştürülür veya `backend/app` içine taşınır)
- [x] CPU-yoğun analiz işlemlerinin `asyncio.to_thread` veya `BackgroundTasks` ile event loop'u bloklamadan çalıştırılması
- [x] Ayıklanan video dosyalarının `backend/app/media/` altında statik dosya olarak sunulması (`StaticFiles`)
**Kabul Kriterleri:**
- `/api/v1/analyze` endpoint'i çağrıldığında istek bloklanmadan (event loop donmadan) analiz tamamlanıyor
- Ayıklanan video `/media/...` yolundan tarayıcıda erişilebiliyor
**Notlar/Riskler:**
- Yok.

---

### Gün 14 — JSON Yanıt Şemasının Tasarlanması
**Hedef:** API'nin döneceği yanıt yapısını kullanıcının belirttiği alanlarla netleştirmek.
**Alt Görevler:**
- [x] `AnalyzeResponse` Pydantic modeline şu alanların eklenmesi:
  - `polyglot_status: bool`
  - `threat_score: int` (0-100)
  - `extracted_video_url: str | None`
  - `analysis_summary: str`
- [x] `threat_score` hesaplama mantığının tanımlanması (trailer tespiti + entropy farkı + boyut sapması sinyallerinin ağırlıklı birleşimi)
- [x] `analysis_summary` metninin dinamik olarak (tespit edilen video boyutu/codec bilgisiyle) oluşturulması
**Kabul Kriterleri:**
- API yanıtı örnek bir polyglot dosya için `polyglot_status: true`, anlamlı bir `threat_score` ve dolu bir `extracted_video_url` döndürüyor
- Temiz bir dosya için `polyglot_status: false` ve düşük `threat_score` döndürüyor
**Notlar/Riskler:**
- Yok.

---

### Gün 15 — Swagger Testleri ve Hata Yönetimi
**Hedef:** API'nin uçtan uca test edilmesi ve hata senaryolarının ele alınması.
**Alt Görevler:**
- [ ] Swagger UI (`/docs`) üzerinden en az 3 farklı dosya ile manuel test yapılması
- [ ] Bozuk/geçersiz dosya, çok büyük dosya, desteklenmeyen format için `HTTPException` ile anlamlı hata mesajları döndürülmesi
- [ ] Global exception handler (`@app.exception_handler`) ile beklenmeyen hataların yakalanması
**Kabul Kriterleri:**
- Tüm hata senaryolarında API 500 yerine anlamlı HTTP durum kodları (400, 413, 422 vb.) ve JSON hata mesajı döndürüyor
**Notlar/Riskler:**
- Yok.

**Hafta 3 Çıktısı:** Dışarıdan sorgulanabilir, tam fonksiyonel Steganaliz REST API Servisi.

---

## 4. Hafta: Web Dashboard (Frontend) Entegrasyonu, Test & Raporlama

### Gün 16 — Sürükle-Bırak Yükleme Arayüzü
**Hedef:** Kullanıcının şüpheli dosyayı yükleyebileceği basit bir web arayüzü tasarlamak.
**Alt Görevler:**
- [ ] `frontend/index.html`, `frontend/style.css`, `frontend/app.js` dosyalarının oluşturulması
- [ ] Sürükle-bırak (drag & drop) dosya yükleme alanının HTML5/JS ile implementasyonu
- [ ] Yükleme sırasında basit bir yükleniyor (loading) göstergesi
**Kabul Kriterleri:**
- Arayüz tarayıcıda açılıp bir dosya sürükle-bırak ile seçilebiliyor
**Notlar/Riskler:**
- Yok.

---

### Gün 17 — Frontend-Backend Entegrasyonu ve Sonuç Gösterimi
**Hedef:** Analiz sonuçlarının ve ayıklanan videonun arayüzde gösterilmesi.
**Alt Görevler:**
- [ ] `app.js` içinde `fetch` ile `/api/v1/analyze` endpoint'ine dosya gönderilmesi
- [ ] `threat_score`in görsel bir gösterge (renkli bar/rozet) ile gösterilmesi
- [ ] `analysis_summary` metninin ekranda gösterilmesi
- [ ] `extracted_video_url` doluysa HTML5 `<video>` player ile videonun oynatılması
- [ ] CORS ayarlarının FastAPI tarafında (`CORSMiddleware`) yapılandırılması
**Kabul Kriterleri:**
- Bir polyglot dosya yüklendiğinde risk skoru, özet ve gömülü video player tarayıcıda görüntüleniyor
**Notlar/Riskler:**
- Yok.

---

### Gün 18 — Uçtan Uca Doğrulama Testleri
**Hedef:** Sistemin temiz ve polyglot dosyalarla bütünsel olarak doğrulanması.
**Alt Görevler:**
- [ ] En az 5 farklı temiz görsel ve 5 farklı polyglot dosya ile arayüz üzerinden manuel test
- [ ] Sonuçların `docs/test-sonuclari.md` dosyasına (Gün 10'daki tabloya ek olarak) işlenmesi
- [ ] Bulunan hataların/eksiklerin giderilmesi
**Kabul Kriterleri:**
- Tüm test senaryoları beklenen `polyglot_status` sonucunu veriyor
**Notlar/Riskler:**
- Yok.

---

### Gün 19 — Dokümantasyon ve GitHub Deposu Düzenleme
**Hedef:** Projenin paylaşılabilir/sunulabilir hale getirilmesi.
**Alt Görevler:**
- [ ] `README.md` dosyasının kurulum, kullanım ve mimari açıklamalarıyla genişletilmesi
- [ ] Kod içi docstring'lerin gözden geçirilmesi (yalnızca gerekli olan yerlerde)
- [ ] `docs/` klasörünün (format notları, test sonuçları) düzenlenmesi
- [ ] (Opsiyonel) Git deposunun oluşturulup ilk commit'in atılması
**Kabul Kriterleri:**
- `README.md` takip edilerek proje sıfırdan kurulup çalıştırılabiliyor
**Notlar/Riskler:**
- Git init/commit işlemi kullanıcı onayı gerektirir, otomatik yapılmayacak.

---

### Gün 20 — Sunum ve Staj Raporu Teslimi
**Hedef:** Proje sonuçlarının akademik danışmana sunulması.
**Alt Görevler:**
- [ ] Kısa bir demo akışının hazırlanması (temiz dosya → polyglot dosya → analiz → ayıklama → oynatma)
- [ ] Staj raporu taslağının (`docs/staj-raporu.md`) tamamlanması: özet, yöntem, karşılaşılan zorluklar, sonuçlar
- [ ] Canlı sistem demosunun prova edilmesi
**Kabul Kriterleri:**
- Demo akışı baştan sona hatasız çalışıyor
- Staj raporu taslağı tüm bölümleriyle tamamlanmış
**Notlar/Riskler:**
- Yok.

**Hafta 4 Çıktısı:** Tamamlanmış web tabanlı tespit paneli ve staj final raporu.

---

## Genel Notlar
- Bu plan bir yol haritasıdır; günler arasında geçiş ihtiyaca göre esnetilebilir (örn. bir gün erken biterse bir sonraki güne geçilebilir).
- Proje kapsamı yalnızca savunma/eğitim amaçlıdır; gerçek X (Twitter) API'sinden veri çekme veya scraping bu projenin bir parçası değildir — tüm test dosyaları sentetik olarak üretilir.
