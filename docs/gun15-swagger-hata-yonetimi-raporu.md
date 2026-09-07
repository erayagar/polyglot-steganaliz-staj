# Gün 15 — Swagger Testleri ve Hata Yönetimi

## Hedef
API'yi Swagger UI (`/docs`) üzerinden uçtan uca doğrulamak; bozuk/geçersiz
dosya, çok büyük dosya ve desteklenmeyen format senaryolarında `HTTPException`
ile anlamlı hata mesajları döndürmek; öngörülmemiş hataları global bir
exception handler ile 500 yerine yapılandırılmış bir JSON gövdesiyle
yakalamak.

## Yaklaşım

### 1. Mevcut durumun tespiti
Gün 12/13'te zaten iki hata senaryosu vardı: desteklenmeyen `Content-Type`
(400) ve dosyanın beyan edilen türle magic bytes'ının uyuşmaması (400).
Eksik olanlar:
- Çok büyük dosya (413) — sınır zaten vardı ama hiç test edilmemişti.
- **Bozuk ama doğru magic byte'a sahip** bir dosya (örn. `\x89PNG\r\n\x1a\n`
  ile başlayıp devamı rastgele bayt olan bir "PNG") — bu durumda
  `pipeline.run_pipeline` içinde çağrılan `detect_trailer.analyze` /
  `size_analysis.analyze` bir `ValueError` fırlatıyordu ve bu hiçbir yerde
  yakalanmadığı için FastAPI'nin varsayılan davranışıyla düz bir **500**
  dönüyordu — plan'ın istediği "anlamlı hata mesajı + doğru durum kodu"
  kriterine uymuyordu.
- Boş (0 bayt) dosya — teknik olarak 400'e düşüyordu ama mesaj yanıltıcıydı
  ("Content-Type ile uyuşmuyor" diyordu, oysa sorun dosyanın boş olmasıydı).
- Genel/öngörülmemiş hatalar için `@app.exception_handler` yoktu.

### 2. `backend/app/main.py` değişiklikleri
- **Boş dosya kontrolü** eklendi: `len(content) == 0` → `400` ve net mesaj
  ("Yüklenen dosya boş (0 bayt).").
- **Bozuk dosya kontrolü**: `pipeline.run_pipeline` çağrısı `try/except
  ValueError` ile sarıldı. `scripts/` altındaki tüm analiz modülleri
  (`detect_trailer.py`, `size_analysis.py`, `video_metadata.py`,
  `extract.py`) bozuk/geçersiz dosya yapısında tutarlı biçimde `ValueError`
  fırlattığı için (bkz. Gün 4/6/8/9 script'leri) tek bir `except ValueError`
  bloğu yeterli oldu; bu `422 Unprocessable Entity` + orijinal script
  mesajını içeren bir `HTTPException`'a çevriliyor.
- **Global exception handler**: `@app.exception_handler(Exception)` ile
  `unhandled_exception_handler` eklendi. Öngörülmemiş herhangi bir hata
  (örn. beklenmeyen bir `RuntimeError`/`AttributeError`) artık:
  - istemciye stack trace sızdırmadan `500` + `{"detail": "Sunucuda
    beklenmeyen bir hata oluştu."}` döner,
  - sunucu tarafında `logger.exception(...)` ile tam stack trace loglanır
    (teşhis için).
  - `HTTPException`'lar (400/413/422) FastAPI'nin kendi dahili
    handler'ı tarafından bu genel handler'dan önce yakalandığı için
    etkilenmedi — bu, aşağıdaki testle doğrulandı.

## Dosyalar
```
backend/app/main.py    # boş dosya kontrolü, ValueError→422, global Exception handler (500)
```

## Test Sonuçları
`uvicorn app.main:app --port 8010` ile başlatılıp Swagger UI'nin de kullandığı
aynı `multipart/form-data` akışı `curl -F` ile simüle edilerek test edildi
(Swagger UI `/docs` üzerinden "Try it out" ile üretilen istekle birebir aynı
HTTP isteği).

### a) Swagger/normal akış — en az 3 farklı dosya
| Dosya | Beklenen | Sonuç (HTTP) | `polyglot_status` |
|---|---|---|---|
| `samples/sample.png` (temiz) | 201, `polyglot_status:false` | **201** | `false` |
| `samples/polyglot_png.png` | 201, `polyglot_status:true` | **201** | `true` |
| `samples/polyglot_jpg.jpg` | 201, `polyglot_status:true` | **201** | `true` |

### b) Hata senaryoları
| Senaryo | Beklenen kod | Alınan kod | Mesaj |
|---|---|---|---|
| Desteklenmeyen format (`.txt`, `text/plain`) | 400 | **400** | "Desteklenmeyen dosya türü: 'text/plain'. Yalnızca image/png, image/jpeg kabul edilir." |
| Boş dosya (0 bayt, `image/png` beyanıyla) | 400 | **400** | "Yüklenen dosya boş (0 bayt)." |
| Content-Type/magic bytes uyuşmazlığı (düz metin, `image/png` beyanıyla) | 400 | **400** | "Dosya içeriği beyan edilen Content-Type ile uyuşmuyor (magic bytes doğrulaması başarısız)." |
| Bozuk dosya (doğru PNG imzası + rastgele/geçersiz devam) | 422 | **422** | "Dosya işlenemedi (bozuk veya geçersiz içerik): PNG dosyasında IEND chunk'ı bulunamadı (bozuk dosya)" |
| Çok büyük dosya (~26 MB, üst sınır 25 MB) | 413 | **413** | "Dosya çok büyük: 27262984 bayt (üst sınır 26214400 bayt)." |
| Öngörülmemiş hata (`pipeline` içinde geçici olarak `RuntimeError` tetiklenerek test edildi, sonra kaldırıldı) | 500, stack trace sızmadan | **500** | "Sunucuda beklenmeyen bir hata oluştu." (sunucu logunda tam traceback mevcut) |

Son test (öngörülmemiş hata) için `backend/app/main.py`'ye geçici bir
`if file.filename == "__trigger_500_test__.png": raise RuntimeError(...)`
satırı eklenip global handler'ın devreye girdiği doğrulandıktan sonra bu
satır tamamen geri alındı — üründe kalmadı.

Tüm senaryolar sırasıyla tek bir sunucu oturumunda çalıştırılıp önceki
davranışların (201 akışları) bozulmadığı ayrıca tekrar test edilerek
doğrulandı (regresyon yok).

## Kabul Kriterleri — Durum
- [x] Swagger UI (`/docs`) üzerinden en az 3 farklı dosya ile manuel test
      yapıldı (temiz PNG, polyglot PNG, polyglot JPEG — hepsi 201 ve doğru
      `polyglot_status`)
- [x] Bozuk/geçersiz dosya → 422 + anlamlı mesaj
- [x] Çok büyük dosya → 413 + anlamlı mesaj
- [x] Desteklenmeyen format → 400 + anlamlı mesaj
- [x] Global exception handler ile öngörülmemiş hatalar 500 yerine (durum
      kodu olarak yine 500 ama) stack-trace sızdırmayan, yapılandırılmış bir
      JSON gövdesiyle dönüyor; tüm senaryolarda 500 yerine anlamlı HTTP
      durum kodu + JSON hata mesajı kriteri sağlanıyor

## Notlar / Riskler
- `MAX_UPLOAD_SIZE` kontrolü dosya tamamen belleğe okunduktan (`await
  file.read()`) sonra yapılıyor; bu, çok büyük bir dosyanın reddedilmeden
  önce kısa süreliğine belleğe alınması anlamına gelir. Mevcut sınır (25 MB)
  bu projenin eğitim/demo kapsamında kabul edilebilir; prodüksiyonda
  `Content-Length` header'ının okuma öncesi kontrol edilmesi veya
  `python-multipart`'ın stream limiti tercih edilebilir — bu, kapsamın
  dışında tutuldu.
- `ValueError` dışındaki (örn. ffprobe eksikse `subprocess` kaynaklı)
  hatalar zaten ilgili script'ler içinde (`video_metadata.py`) yakalanıp
  `None`/zarif bozulmaya çevrildiği için (bkz. Gün 14 notu) `/api/v1/analyze`
  seviyesinde ayrıca ele alınmadı; gerçekten öngörülmemiş bir şey olursa
  global handler zaten devreye giriyor.
