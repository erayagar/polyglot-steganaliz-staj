# Test Sonuçları

Bu dosya, Gün 10 (ve ilerleyen günlerde Gün 18) test senaryolarının ve
tespit başarımı ölçümlerinin sonuçlarını içerir.

---

## Gün 10 — Farklı Senaryolarda Tespit Başarımının Ölçülmesi

### Hedef
Görsel sıkıştırma ve farklı format kombinasyonlarında sistemin (`detect_trailer`
+ `entropy` + `size_analysis`) tespit başarımını, özellikle yanlış pozitif /
yanlış negatif oranlarını ölçmek.

### Yeni araçlar
- **`scripts/analyze.py`** — `detect_trailer`, `size_analysis` ve `entropy`
  modüllerini tek bir pipeline'da birleştirip birleşik bir JSON/insan-okur
  rapor üreten script (Gün 1-2 haftalarını birleştiren `analyze.py`, plandaki
  "Hafta 2 Çıktısı" hedefiyle uyumlu). Hiçbir sinyali tek başına "kesin karar"
  olarak kullanmaz; üç modülün sonucunu da yan yana raporlar.
- **`scripts/make_test_scenarios.py`** — Aşağıdaki senaryo 3 ve ek senaryo 4
  dosyalarını `samples/test_matrix/` altına üreten, tekrar çalıştırılabilir
  script.

### Test Senaryoları (4 kategori, 10 dosya)

| Kategori | Dosya | Üretim yöntemi |
|---|---|---|
| 1. PNG+MP4 polyglot | `samples/polyglot_png.png` | Gün 3, `make_polyglot.py` |
| 2. JPEG+MP4 polyglot | `samples/polyglot_jpg.jpg` | Gün 3, `make_polyglot.py` |
| 3a. Yeniden sıkıştırılmış polyglot (embed **sonrası**) | `samples/test_matrix/recompressed_post_png.png` | Var olan PNG polyglotu PIL (`Image.open().load().save(optimize=True)`) ile yeniden kaydetme — bir platformun görseli sunucu tarafında yeniden encode etmesini simüle eder |
| 3a. Yeniden sıkıştırılmış polyglot (embed **sonrası**) | `samples/test_matrix/recompressed_post_jpg.jpg` | Aynı yöntem, JPEG polyglot + `quality=75` |
| 3b. Yeniden sıkıştırılmış polyglot (embed **öncesi**) | `samples/test_matrix/recompressed_pre_png.png` | Taşıyıcı PNG önce farklı sıkıştırma seviyesiyle (`compress_level=9`) kaydedilip, video bu yeni taşıyıcıya eklendi |
| 3b. Yeniden sıkıştırılmış polyglot (embed **öncesi**) | `samples/test_matrix/recompressed_pre_jpg.jpg` | Aynı yöntem, taşıyıcı JPEG `quality=50` ile kaydedilip video eklendi |
| 4. Temiz görsel | `samples/sample.png` | Gün 1 örneği, video içermiyor |
| 4. Temiz görsel | `samples/sample.jpg` | Gün 1 örneği, video içermiyor |
| 4. Temiz görsel (LSB stego, trailer yok) | `samples/lsb_stego_sample.png` | Gün 7 LSB steganografi örneği — gizli veri var ama trailer-append **değil** |
| 4. Temiz görsel (farklı boyut) | `samples/test_matrix/clean_gradient.png` | 128×128 sentetik gradient, video içermiyor |

**Zemin gerçeği (ground truth):** #1, #2 ve 3b'nin iki dosyası (toplam 4 dosya)
gerçekten gizli video içeriyor; 3a'nın iki dosyası ve kategori 4'ün dört dosyası
(toplam 6 dosya) gerçek video içermiyor (3a'da video, recompression sırasında
fiilen yok ediliyor — bkz. Bulgular).

### Sonuç Tablosu

Her dosya için `python scripts/analyze.py --file <dosya> --json` çalıştırıldı.

| # | Dosya | Gerçek durum | `trailer.polyglot_status` | `size.suspicious` (sapma) | `entropy.entropy_delta` (sınır offset) | Trailer sonucu |
|---|---|---|---|---|---|---|
| 1 | `polyglot_png.png` | polyglot | **EVET** | EVET (+49.3%) | 1.033 (offset 217) | ✅ doğru |
| 2 | `polyglot_jpg.jpg` | polyglot | **EVET** | EVET (+294.0%) | 1.143 (offset 1371) | ✅ doğru |
| 3a-png | `recompressed_post_png.png` | temiz* | hayır | hayır (−92.8%) | n/a (sınır yok) | ✅ doğru |
| 3a-jpg | `recompressed_post_jpg.jpg` | temiz* | hayır | hayır (−51.9%) | n/a (sınır yok) | ✅ doğru |
| 3b-png | `recompressed_pre_png.png` | polyglot | **EVET** | EVET (+47.7%) | 0.892 (offset 178) | ✅ doğru |
| 3b-jpg | `recompressed_pre_jpg.jpg` | polyglot | **EVET** | EVET (+256.4%) | 1.318 (offset 909) | ✅ doğru |
| 4 | `sample.png` | temiz | hayır | hayır (−91.2%) | n/a | ✅ doğru |
| 4 | `sample.jpg` | temiz | hayır | hayır (+11.6%) | n/a | ✅ doğru |
| 4 | `lsb_stego_sample.png` | temiz | hayır | **EVET (+45.6%)** ⚠️ | n/a | ✅ doğru (trailer) / ❌ yanlış (size) |
| 4 | `clean_gradient.png` | temiz | hayır | hayır (−96.3%) | n/a | ✅ doğru |

\* 3a dosyalarında zemin gerçeği "temiz" olarak işaretlendi çünkü recompression
işlemi videoyu fiilen siliyor (dosya artık gerçekten video içermiyor) — bkz.
aşağıdaki Bulgular #2.

### Bulgular

1. **Ana tespit sinyali (`detect_trailer`, trailer-append tabanlı
   `polyglot_status`) 10/10 dosyada doğru sonuç verdi — %0 false-positive,
   %0 false-negative.** Taşıyıcının embed öncesi farklı bir sıkıştırma
   seviyesiyle kaydedilmesi (senaryo 3b) tespiti hiç etkilemedi; trailer
   tespiti EOF sonrası baytları taradığı için taşıyıcının iç sıkıştırma
   detaylarından bağımsız çalışıyor.

2. **Embed *sonrası* yeniden sıkıştırma (senaryo 3a), trailer'ı tamamen
   yok ediyor.** PIL gibi bir kod çözücü/kodlayıcı, görseli yalnızca kendi
   dekode ettiği piksel verisinden yeniden yazdığı için EOF sonrasındaki
   gizli video baytları kayboluyor (`recompressed_post_png.png`: 3688 →
   178 bayt, `recompressed_post_jpg.jpg`: 4842 → 591 bayt). Sistem bu
   dosyaları doğru şekilde "temiz" olarak raporluyor — ancak bu bir
   **tespit hatası değil**, çünkü gizli video verisi bu noktada adli
   olarak gerçekten kurtarılamaz hale gelmiştir (plandaki Gün 10 risk
   notuyla birebir örtüşüyor: "Görsel optimizasyon araçları bazen trailer
   verisini bozabilir"). Pratik sonucu: bir platformun görseli sunucu
   tarafında yeniden encode etmesi (ör. X/Twitter'ın yükleme sonrası
   görselleri işlemesi), bu tip trailer-append polyglot'ları kendiliğinden
   etkisiz hale getiriyor.

3. **`size_analysis` tek başına kullanıldığında çok daha gürültülü bir
   sinyal.** `lsb_stego_sample.png` dosyasında trailer yok (video yok)
   ama LSB steganografi PNG'nin gerçek bayt boyutunu Gün 6'daki basit
   "~%20 sıkıştırma oranı" varsayımının ötesine taşıdığı için sapma
   %45.6 çıkıyor ve dosya "şüpheli" işaretleniyor — **tek başına
   `size_analysis` için bir false-positive.** JPEG polyglot'larda da sapma
   oranı çok değişken (+%294, +%256) — Gün 6 risk notuyla uyumlu şekilde
   JPEG sıkıştırma oranının içeriğe bağlı olması bu sinyali tek başına
   güvenilmez kılıyor.

4. **`entropy.entropy_delta` yalnızca `detect_trailer` bir sınır offset'i
   bulduğunda hesaplanabiliyor** (bu script'in tasarımı gereği, bkz.
   `scripts/entropy.py`'daki `find_boundary_offset`), yani bağımsız bir
   tespit sinyali değil, trailer tespitini doğrulayan/görselleştiren
   tamamlayıcı bir sinyal. Tüm polyglot dosyalarında görsel bölgesi
   (ortalama entropy ~6.0-6.4) ile video bölgesi (~5.1-5.2) arasında
   belirgin bir düşüş var; bu fark grafikte de görünür
   (`docs/gun10-entropy-recompressed_pre_png.png`: taşıyıcı farklı
   sıkıştırmayla üretilmiş olsa bile sınır hâlâ net görünüyor,
   `docs/gun10-entropy-recompressed_post_png.png`: trailer silindiği için
   sınır çizgisi yok).

### Yanlış Pozitif / Yanlış Negatif Oranları

| Sinyal | Temiz dosyalarda FP | Polyglot dosyalarda FN |
|---|---|---|
| **`trailer.polyglot_status` (ana karar)** | **0/6 = %0** | **0/4 = %0** |
| `size.suspicious` (tek başına) | 1/6 = %16.7 (`lsb_stego_sample.png`) | 0/4 = %0 |

**Sonuç:** Ana tespit mekanizması olan trailer-append taraması, temiz
dosyalarda kabul kriterinin gerektirdiği gibi %0'a yakın (bu testte tam
olarak %0) false-positive veriyor. `size_analysis` ve `entropy`, plandaki
tasarım niyetine uygun şekilde tek başına karar mercii değil, tamamlayıcı/
doğrulayıcı sinyaller olarak konumlandırılmalı (Gün 6 ve Gün 7 notlarıyla
tutarlı).

### Sınır Durumlar / Riskler

- Embed sonrası yeniden sıkıştırma (senaryo 3a), trailer-append
  polyglot'ları etkisiz hale getiriyor — bu hem bir sınırlama (adli
  olarak veri kurtarılamıyor) hem de yan etkisi olumlu bir savunma
  mekanizması (platformun kendi görsel işleme pipeline'ı, kötü amaçlı
  yükü kendiliğinden temizliyor).
- LSB steganografi (trailer içermeyen), `size_analysis` sinyalini
  yanıltabiliyor; bu nedenle `size_analysis` asla tek başına "polyglot"
  kararı vermek için kullanılmamalı, yalnızca `detect_trailer` sonucunu
  destekleyen ikincil bir gösterge olarak ele alınmalı.

### Kabul Kriterleri — Durum

- [x] `docs/test-sonuclari.md` en az 4 senaryo için sonuç satırı içeriyor
      (4 kategori, 10 dosya, tam sonuç tablosu yukarıda)
- [x] Sistem temiz dosyalarda %0'a yakın false-positive veriyor (ana
      trailer sinyali: 6 temiz dosyada tam olarak %0 FP)
