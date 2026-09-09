# Gün 18 — Uçtan Uca Doğrulama Testleri

## Hedef
Gün 1-17'de geliştirilen sistemi (steganaliz motoru + FastAPI backend +
web arayüzü) CLI script'leri üzerinden değil, **gerçek dağıtılmış web
uygulaması** üzerinden en az 5 temiz ve 5 polyglot dosya ile uçtan uca
doğrulamak; sonuçları `docs/test-sonuclari.md`'ye işlemek; test sırasında
bulunan hataları/eksikleri gidermek.

Bu gün, Gün 10'un ("Farklı Senaryolarda Tespit Başarımının Ölçülmesi")
doğal devamıdır ama farklı bir katmanı test eder: Gün 10 `scripts/analyze.py`
(saf CLI pipeline) ile test etmişti; Gün 18 Gün 11-17'de inşa edilen HTTP
API + CORS + frontend entegrasyon katmanının da doğru çalıştığını,
tespit doğruluğunu bozmadığını doğrular.

## Yaklaşım

### 1. Ön kontrol — Gün 1-17 eksiksizlik
`PLAN.md`'deki Gün 1-17 alt görev kutucuklarının tamamı `- [x]`, her gün
için referans verilen script/kod dosyaları (`scripts/*.py` — 9 dosya,
`backend/app/{main,models,pipeline}.py`, `frontend/{index.html,app.js,
style.css}`) diskte mevcut ve her gün için `docs/gunN-*.md` + `.pdf` raporu
bulunuyor (Gün 2 hariç, o yalnızca PDF — bilinen/kabul edilmiş durum).
Ek olarak `python scripts/analyze.py --file samples/polyglot_png.png --json`
ile CLI pipeline'ın hâlâ sorunsuz çalıştığı teyit edildi.

### 2. Test dosyalarının hazırlanması
Gün 10'daki 10 dosyalık matris (hepsi hâlâ `samples/` altında, `.gitignore`
ile git dışı tutuluyor) yeniden kullanıldı. Yalnızca eski senaryoları
tekrarlamak yerine gerçekten yeni kapsam eklemek için, `scripts/
make_polyglot.py` ile **iki yeni, daha önce hiç kullanılmamış taşıyıcı
görselden** iki yeni polyglot üretildi (`samples/sample.mp4` gömülerek):

- `samples/test_matrix/polyglot_checker_png.png` — yeni 96×96 checkerboard PNG taşıyıcı
- `samples/test_matrix/polyglot_solid_jpg.jpg` — yeni 100×100 düz renk JPEG taşıyıcı

Toplam **6 temiz + 6 polyglot = 12 dosya** ile plandaki "en az 5+5"
kriteri güvenli bir marjla karşılandı.

### 3. Sistemin ayağa kaldırılması ve test yöntemi
Backend (`uvicorn app.main:app`, `127.0.0.1:8000`) ve frontend (`python3 -m
http.server`, `127.0.0.1:5500`) Gün 17'deki gibi ayrı origin'lerden ayağa
kaldırıldı. Bu oturumda `claude-in-chrome` tarayıcı eklentisi bağlı
değildi (kullanıcı kurulumu ertelendi — Gün 16/17'deki kısıtla aynı), bu
yüzden gerçek tıklama/sürükle-bırak etkileşimi görsel olarak otomatik
doğrulanamadı.

Bunun yerine, `frontend/app.js`'in `analyzeFile()` fonksiyonunun attığı
isteğin **birebir aynısı** — `POST /api/v1/analyze`, `multipart/form-data`,
`Origin: http://127.0.0.1:5500` header'ıyla — her 12 dosya için
gönderildi. Dönen `extracted_video_url` alanı doluysa, o URL de aynı
`Origin` header'ıyla `GET` ile çekilip `200 OK` + `content-type:
video/mp4` döndüğü doğrulandı; bu, arayüzdeki `<video src>` elemanının
gerçekten oynatılabilir bir kaynağa işaret ettiğini kanıtlar (Gün 17'nin
CORS doğrulamasının 12 dosyaya genişletilmiş hali).

Ayrıca Gün 15'in hata yolları da regresyon olarak yeniden tetiklendi:
desteklenmeyen dosya türü ve boş (0 bayt) dosya.

### 4. Sonuçların değerlendirilmesi ve hata giderme
12 dosyanın tamamı beklenen `polyglot_status` sonucunu verdi (0 FP, 0 FN);
backend logunda 14 istek boyunca hiçbir `500` görülmedi. Bu nedenle kod
değişikliği gerektiren bir hata/eksik **bulunmadı** — Gün 18'in "bulunan
hataların giderilmesi" alt görevi için düzeltilecek bir şey yoktu (bu,
uydurma bir "hata yok" iddiası değil, aşağıdaki test sonuçlarıyla
doğrulanmış bir gözlemdir).

## Dosyalar
```
docs/test-sonuclari.md                        # Gün 18 bölümü eklendi (12 satırlık sonuç tablosu)
docs/gun18-uctan-uca-dogrulama-raporu.md/.pdf  # bu rapor
PLAN.md                                        # Gün 18 alt görevleri işaretlendi
samples/test_matrix/polyglot_checker_png.png   # yeni test dosyası (gitignored)
samples/test_matrix/polyglot_solid_jpg.jpg     # yeni test dosyası (gitignored)
README.md                                      # durum Gün 17 → Gün 18
```

## Test Sonuçları

| # | Dosya | Gerçek durum | `polyglot_status` | `threat_score` | Video erişimi |
|---|---|---|---|---|---|
| 1 | `sample.png` | temiz | false | 0 | — |
| 2 | `sample.jpg` | temiz | false | 2 | — |
| 3 | `lsb_stego_sample.png` | temiz | false | 7 | — |
| 4 | `clean_gradient.png` | temiz | false | 0 | — |
| 5 | `recompressed_post_png.png` | temiz | false | 0 | — |
| 6 | `recompressed_post_jpg.jpg` | temiz | false | 0 | — |
| 7 | `polyglot_png.png` | polyglot | **true** | 76 | 200 `video/mp4` |
| 8 | `polyglot_jpg.jpg` | polyglot | **true** | 85 | 200 `video/mp4` |
| 9 | `recompressed_pre_png.png` | polyglot | **true** | 75 | 200 `video/mp4` |
| 10 | `recompressed_pre_jpg.jpg` | polyglot | **true** | 86 | 200 `video/mp4` |
| 11 | `polyglot_checker_png.png` (yeni) | polyglot | **true** | 66 | 200 `video/mp4` |
| 12 | `polyglot_solid_jpg.jpg` (yeni) | polyglot | **true** | 69 | 200 `video/mp4` |

FP: 0/6 (%0) · FN: 0/6 (%0). Ayrıntılı bulgular ve metodoloji için
`docs/test-sonuclari.md`'deki "Gün 18" bölümüne bakınız.

## Kabul Kriterleri — Durum
- [x] Tüm test senaryoları beklenen `polyglot_status` sonucunu veriyor (12/12)

## Notlar/Riskler
- `claude-in-chrome` bu oturumda da bağlı değildi; HTTP düzeyinde doğrulama
  (frontend'in attığı isteğin birebiri, aynı `Origin` header'ıyla)
  işlevsel olarak eşdeğer olsa da, kullanıcının kendi tarayıcısında en az
  bir polyglot ve bir temiz dosya ile son bir görsel teyit yapması (rozet
  rengi, tehdit bar'ı, video player'ın gerçekten oynatması) önerilir.
- Test matrisindeki dosyaların çoğu (10/12) Gün 10'dan yeniden kullanıldı;
  bu bilinçli bir tercih — amaç steganaliz algoritmasını yeniden test etmek
  değil, HTTP/CORS/statik dosya sunumu entegrasyon katmanının tespit
  doğruluğunu bozmadığını doğrulamaktı. Genuine yeni kapsam için 2 yeni
  taşıyıcıdan üretilen polyglot eklendi (#11, #12).
