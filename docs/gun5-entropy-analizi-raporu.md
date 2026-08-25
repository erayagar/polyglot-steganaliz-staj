# Gün 5 — Shannon Entropy Analizi ve Görselleştirme

## Hedef
Dosya içindeki veri yoğunluğu farklarını Shannon entropy hesabıyla ortaya
çıkarmak; Gün 3'te üretilen polyglot dosyalarda görsel bölgesi ile arkasına
eklenmiş video bölgesi arasındaki entropy farkını grafik üzerinde görünür
kılmak.

## Yaklaşım

### 1. Blok bazlı Shannon entropy hesabı
Dosya sabit boyutlu bloklara (`--block-size`, varsayılan 256 bayt) bölünüyor.
Her blok için, blok içindeki bayt değerlerinin frekans dağılımından klasik
Shannon entropy formülü uygulanıyor:

```
H = -Σ p(x) · log2(p(x))     (x: 0-255 arası bayt değeri)
```

Sonuç, bayt başına 0-8 bit aralığında bir değer. 8'e yakın değerler
"rastgele/sıkıştırılmış/yüksek yoğunluklu" veriyi, düşük değerler ise
tekrarlayan/öngörülebilir veriyi (ör. düz renk alanları, header/padding)
işaret ediyor.

### 2. Görsel/video sınırının grafiğe işlenmesi
Her blok bağımsız hesaplandığından, script ayrıca Gün 4'teki
`detect_trailer.analyze()` fonksiyonunu içe aktararak dosyanın gizli video
başlangıç offset'ini (varsa) buluyor ve bunu grafikte kırmızı kesikli dikey
çizgi olarak işaretliyor. Dosya PNG/JPEG değilse veya trailer'da bilinen bir
video imzası yoksa çizgi hiç çizilmiyor — bu da kod tekrarını önlerken
(Gün 4 mantığının yeniden kullanılması) iki günün çıktısını tek grafikte
birleştiriyor.

### 3. Görselleştirme ve dosya adlandırma
matplotlib ile `offset → entropy` çizgi grafiği çiziliyor, `Agg` backend
kullanılarak GUI'siz (headless) ortamda da çalışması sağlandı. Çıktı dosya
adı, iki farklı formattaki aynı köke sahip dosyalar (`sample.png` /
`sample.jpg`) arasında çakışmayı önlemek için tam dosya adından türetiliyor
(`entropy-sample_png.png`, `entropy-sample_jpg.png`) — geliştirme sırasında
bu çakışma fark edilip düzeltildi.

## Script: `scripts/entropy.py`

```
python scripts/entropy.py --file <dosya>
python scripts/entropy.py --file <dosya> --block-size 512 --output <çıktı.png>
python scripts/entropy.py --file <dosya> --json
```

Varsayılan çıktı: `docs/entropy-<dosya_adı>.png`. `--json` bayrağı, her
bloğun `offset`, `size` ve `entropy` alanlarını ayrıca konsola yazdırıyor.

## Test Sonuçları

| Dosya | Blok sayısı | Sınır offset | Grafikte gözlem |
|---|---|---|---|
| `samples/polyglot_png.png` | 15 | 217 (`0xD9`) | Sınırın hemen öncesinde/sonrasında belirgin entropy değişimi; video verisinin (H.264/MP4 konteyner) ~7 bit/bayt civarı yüksek ve görece düz seyrettiği bölge net ayırt ediliyor |
| `samples/polyglot_jpg.jpg` | 19 | 1371 (`0x55B`) | Fark PNG'ye göre daha az belirgin — JPEG kendisi de zaten sıkıştırılmış olduğundan görsel bölgesi de yüksek entropili; yine de sınır civarında hafif bir düşüş/toparlanma gözlemleniyor |
| `samples/sample.png` (temiz) | 1 | tespit edilemedi | Sınır çizgisi yok (beklenen davranış) |
| `samples/sample.jpg` (temiz) | 6 | tespit edilemedi | Sınır çizgisi yok, entropy tüm dosya boyunca homojen yüksek (tipik sıkıştırılmış JPEG karakteristiği) |

Üretilen grafikler: `docs/entropy-polyglot_png_png.png`,
`docs/entropy-polyglot_jpg_jpg.png`, `docs/entropy-sample_png.png`,
`docs/entropy-sample_jpg.png`.

### Görsel: PNG polyglot (net ayrım)
![PNG polyglot entropy grafiği](entropy-polyglot_png_png.png)

### Görsel: JPEG polyglot (daha zayıf ayrım)
![JPEG polyglot entropy grafiği](entropy-polyglot_jpg_jpg.png)

## Kabul Kriterleri — Durum

- [x] Üretilen entropy grafiğinde görsel/video geçiş noktası görsel olarak
      ayırt edilebiliyor (PNG'de net, JPEG'de daha zayıf ama gözlemlenebilir)
- [x] Grafik `docs/` altına PNG olarak kaydedilebiliyor

## Notlar / Riskler

- Plan'da öngörülen risk doğrulandı: **sıkıştırılmış görsellerde (JPEG)
  görsel/video ayrımı PNG'ye göre daha zordur**, çünkü JPEG'in kendisi
  DCT tabanlı sıkıştırma sonucu zaten yüksek entropili veri üretir; PNG ise
  sıkıştırmasız/az sıkıştırılmış olduğundan video verisiyle kontrastı daha
  belirgindir. Bu bulgu, tek başına entropy analizinin JPEG polyglot'larda
  yeterli bir sinyal olmayabileceğini, Gün 4'teki trailer/imza tespiti ile
  birlikte kullanılması gerektiğini destekliyor.
- Blok boyutu (`--block-size`) sonucu doğrudan etkiliyor: çok küçük bloklar
  (örn. 16 bayt) gürültülü/dalgalı bir grafik üretirken çok büyük bloklar
  (örn. 4096 bayt) sınırdaki geçişi bulanıklaştırabilir; 256 bayt varsayılan
  değeri bu projedeki küçük örnek dosyalar için dengeli bir çözünürlük
  sağladı.
- `find_boundary_offset()`, `detect_trailer.analyze()`'ı çağırırken
  `ValueError`/`FileNotFoundError` yakalıyor; böylece PNG/JPEG olmayan bir
  dosya (ör. ham `.mp4`) `entropy.py`'ye verildiğinde sınır çizgisi
  gösterilmeden grafik yine de üretiliyor (script çökmüyor).
