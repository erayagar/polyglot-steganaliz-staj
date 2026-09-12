# Gün 20 — Sunum, Demo Provası ve Staj Raporu Teslimi

## Hedef
Projeyi akademik danışmana sunmaya hazır hale getirmek: (1) baştan sona
hatasız çalışan kısa bir demo akışı hazırlamak ve prova etmek, (2) staj
final raporunu (`docs/staj-raporu.md`) tamamlamak. Bu gün kod davranışını
değiştirmez; yalnızca Gün 1-19'un doğruluğunu bağımsız olarak yeniden
teyit edip kapanış dokümantasyonunu tamamlar.

## Yaklaşım

### 1. Bağımsız doğrulama turu (Gün 1-19'un tamamı)
Staj raporunu yazmadan önce, geriye dönük 19 günün hâlâ iddia edildiği
gibi çalıştığından emin olmak için tüm katmanlar yeniden test edildi:

- **Ortam (Gün 1):** `python -c "import cv2, PIL, fastapi, numpy,
  matplotlib"` ve `ffprobe -version` hatasız çalıştı.
- **CLI pipeline (Gün 3-6):** `scripts/analyze.py --json`,
  `samples/sample.png` (temiz), `samples/polyglot_png.png` ve
  `samples/polyglot_jpg.jpg` (polyglot) üzerinde çalıştırıldı — trailer
  offset'leri (217 / 1371), `detected_signature` (`mp4/ftyp`) ve entropy
  delta'ları (1.033 / 1.143) önceki günlerin raporlarındaki değerlerle
  birebir aynı çıktı.
- **Extraction + metadata (Gün 8-9):** `scripts/extract.py` ile
  `polyglot_png.png`'den video ayıklandı, `scripts/video_metadata.py` ile
  meta verisi okundu: 64x64, 2.0 sn, 20 kare, codec `h264` — Gün 9
  raporuyla tutarlı.
- **API katmanı (Gün 11-15):** `uvicorn` geçici bir portta (8123) ayağa
  kaldırılıp gerçek HTTP istekleriyle test edildi: health-check, temiz/
  polyglot PNG/JPEG analizi, desteklenmeyen tür (400), boş dosya (400),
  ayıklanan videonun `/media/...` üzerinden `video/mp4` olarak servis
  edilmesi (200). Dönen `threat_score` değerleri (0, 76, 85) README'deki
  ve Gün 14 raporundaki örnekle birebir eşleşti. Test sunucusu ve ürettiği
  geçici dosyalar (`backend/tmp/`, `backend/app/media/`) doğrulama
  sonrasında temizlendi.
- **Depo temizliği:** `git status` ile hiçbir istenmeyen/izlenmeyen
  dosyanın ortaya çıkmadığı doğrulandı.

Bu turda **hiçbir hata veya tutarsızlık bulunmadı** — 19 günün tamamı
bugün itibarıyla da geçerli.

### 2. Demo Akışı
Danışmana gösterilecek kısa (≈3 dakikalık) akış, README'nin "Kullanım"
bölümündeki komutlara dayanıyor:

1. **Backend'i başlat:** `cd backend && uvicorn app.main:app --reload`
   → `http://127.0.0.1:8000/docs` (Swagger UI) gösterilir.
2. **Frontend'i başlat:** `cd frontend && python3 -m http.server 5500`
   → `http://127.0.0.1:5500` tarayıcıda açılır.
3. **Temiz dosya:** `samples/sample.png` sürükle-bırak ile yüklenir →
   düşük/sıfır tehdit skoru ve "dosya temiz" özeti gösterilir.
4. **Polyglot dosya:** `samples/polyglot_png.png` (veya `.jpg`) yüklenir →
   yüksek tehdit skoru (rozet kırmızı), tespit edilen imza/offset içeren
   özet metni ve gömülü `<video>` player'ında gizli videonun oynatılması
   gösterilir.
5. **(Opsiyonel) CLI tarafı:** `python scripts/analyze.py --file ... --json`
   ile aynı sonucun API'siz de üretilebildiği, yani `backend/`'in
   `scripts/`'i sarmalayan ince bir katman olduğu gösterilir.

Bu akış, bu oturumda adım adım (backend gerçek sunucu, sırasıyla temiz ve
polyglot dosyalarla) çalıştırılıp **baştan sona hatasız** tamamlandı (bkz.
Bölüm 1 — API katmanı doğrulaması aynı zamanda bu demo provasıdır).

### 3. Sınır Notu (Gün 16-18'den devam eden)
Bu ortamda canlı tarayıcı otomasyonu (`claude-in-chrome`) bulunmuyor; demo
provası HTTP düzeyinde (frontend'in attığı isteğin birebiri, aynı
uç noktalar ve aynı yanıt şeması ile) yapıldı. Gerçek sunum öncesinde
kullanıcının kendi tarayıcısında en az bir temiz ve bir polyglot dosyayla
son bir görsel teyit (rozet rengi, video player'ın gerçekten oynatması)
yapması önerilir — bu, Gün 16/17/18 raporlarında da tutarlı şekilde not
edilen aynı öneridir.

## Kabul Kriterleri — Durum
- [x] Demo akışı baştan sona hatasız çalışıyor (HTTP düzeyinde prova
      edildi; tarayıcıda son görsel teyit kullanıcıya bırakıldı — bkz.
      Bölüm 3)
- [x] Staj raporu taslağı (`docs/staj-raporu.md`) tüm bölümleriyle
      tamamlandı: özet, yöntem, karşılaşılan zorluklar, sonuçlar

## Notlar / Riskler
- Yok — bu bağımsız doğrulama turunda kod değişikliği gerektiren hiçbir
  kusur bulunmadı; 20 günlük plan artık uçtan uca (Gün 1'den Gün 20'ye)
  doğrulanmış durumda.
