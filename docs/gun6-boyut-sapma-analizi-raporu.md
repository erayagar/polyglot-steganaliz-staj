# Gün 6 — Teorik vs Gerçek Dosya Boyutu Sapma Analizi

## Hedef
Görsel çözünürlüğü ve renk derinliğinden beklenen teorik dosya boyutunu
hesaplayıp gerçek dosya boyutuyla karşılaştırmak; gerçek boyutun teorik
boyutu piksel verisiyle açıklanamayacak ölçüde aşması durumunda dosyayı
"şüpheli" olarak işaretlemek.

## Yaklaşım

### 1. Teorik (beklenen) boyut hesabı
Format bazında iki farklı yöntem uygulandı:

- **PNG:** Sıkıştırmasız ham boyut, `IHDR` chunk'ından okunan genişlik,
  yükseklik, bit derinliği ve renk tipinden (renk tipi → kanal sayısı
  eşlemesi: 0→gri, 2→RGB, 3→palet, 4→gri+alfa, 6→RGBA) hesaplanıyor;
  PNG'nin her satır başına 1 filtre baytı eklediği de hesaba katılıyor:
  `ham_boyut = yükseklik × (1 + ⌈genişlik × kanal × bit_derinliği / 8⌉)`.
  Bu ham boyut, tipik bir PNG sıkıştırma oranı varsayımıyla (**%20, ~5:1**)
  ölçeklenerek teorik (beklenen sıkıştırılmış) boyuta çevriliyor.
- **JPEG:** Ham boyut, `SOF0`/`SOF2` marker'ından okunan genişlik × yükseklik
  × bileşen sayısından hesaplanıyor (`genişlik × yükseklik × kanal`, filtre
  baytı yok). Tipik bir JPEG sıkıştırma oranı varsayımıyla (**%10, ~10:1**)
  teorik boyuta ölçekleniyor. JPEG marker taraması, Gün 4'teki
  `detect_trailer.NO_LENGTH_MARKERS` kümesi yeniden kullanılarak yapıldı
  (TEM ve restart marker'larının uzunluk alanı olmadığı bilgisi tekrar
  kodlanmadı).

### 2. Sapma yüzdesi ve eşik
```
sapma_% = (gerçek_boyut − teorik_boyut) / teorik_boyut × 100
```
Sapma **%20**'yi (`DEVIATION_THRESHOLD_PERCENT`) aştığında dosya
`suspicious=true` olarak işaretleniyor. Gerçek boyutun teorik boyutun
*altında* kalması (negatif sapma) beklenen/normal bir durum — sıkıştırma
her zaman ham boyutu küçültür — bu yüzden yalnızca pozitif yönde büyük
sapmalar şüpheli sayılıyor.

## Script: `scripts/size_analysis.py`

```
python scripts/size_analysis.py --file <dosya>
python scripts/size_analysis.py --file <dosya> --json
```

Çıktı alanları: `width`, `height`, `channels`, `raw_uncompressed_size`,
`expected_compression_ratio`, `theoretical_size`, `deviation_percent`,
`threshold_percent`, `suspicious`, `analysis_summary`.

## Test Sonuçları

| Dosya | Format | Boyutlar | Ham boyut | Teorik boyut | Gerçek boyut | Sapma | Şüpheli mi? |
|---|---|---|---|---|---|---|---|
| `samples/sample.png` (temiz) | PNG | 64×64 | 12352 B | 2470 B | 217 B | %-91.2 | hayır |
| `samples/polyglot_png.png` | PNG | 64×64 | 12352 B | 2470 B | 3688 B | **%49.3** | **EVET** |
| `samples/sample.jpg` (temiz) | JPEG | 64×64 | 12288 B | 1229 B | 1371 B | %11.6 | hayır |
| `samples/polyglot_jpg.jpg` | JPEG | 64×64 | 12288 B | 1229 B | 4842 B | **%294.0** | **EVET** |

Her iki temiz dosyada da sapma eşiğin (%20) altında kaldı; her iki polyglot
dosyada da sapma eşiği belirgin bir farkla aştı (JPEG'de video/ham oranı
daha yüksek olduğu için sapma PNG'ye göre çok daha keskin çıktı).

## Kabul Kriterleri — Durum

- [x] Polyglot dosyalarda sapma oranı belirgin şekilde yüksek çıkıyor
      (PNG: %49.3, JPEG: %294.0 — ikisi de %20 eşiğinin üstünde)
- [x] Temiz dosyalarda sapma oranı düşük/normal aralıkta kalıyor
      (PNG: %-91.2, JPEG: %11.6 — ikisi de eşiğin altında)

## Notlar / Riskler

- **Sıkıştırma oranı varsayımları sabit ve içerik-bağımsızdır.** %20 (PNG)
  ve %10 (JPEG) değerleri, bu projedeki basit/sentetik test görselleri için
  kalibre edildi. Yüksek detaylı gerçek fotoğraflarda PNG genelde daha az
  sıkışır (ham boyutun %30-60'ı gibi), bu da teorik boyutu büyütüp yöntemin
  hassasiyetini düşürebilir; JPEG'de ise kalite ayarına göre sıkıştırma
  oranı önemli ölçüde değişir. Bu yöntem, Gün 4 (trailer/imza tespiti) ve
  Gün 5 (entropy) sinyalleriyle birlikte kullanılmalı, tek başına kesin
  kanıt sayılmamalı.
- **Küçük eklenen veri kaçabilir.** Eklenen trailer boyutu, teorik boyutla
  gerçek boyut arasındaki mevcut boşluktan küçükse (özellikle temiz dosya
  zaten teorik boyutun oldukça altındaysa) sapma %20 eşiğini aşmayabilir —
  yöntem küçük/az miktarda eklenmiş veriye karşı görece duyarsızdır.
- JPEG'de sapma oranının PNG'ye göre çok daha yüksek çıkması beklenen bir
  sonuç: JPEG zaten agresif sıkıştırıldığından teorik (beklenen) boyutu
  PNG'ye göre daha küçük, bu da aynı büyüklükteki eklenen video verisinin
  oransal etkisini büyütüyor.
