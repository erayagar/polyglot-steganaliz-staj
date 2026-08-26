# Gün 8 — Extraction (Unpolyglot) Fonksiyonu

## Hedef
Görsel arkasına gizlenmiş MP4 video akışını orijinal görselden ayırıp
bağımsız bir dosya olarak kaydeden `scripts/extract.py` script'ini yazmak;
böylece Gün 4'te yalnızca *tespit* edilen gizli video, gerçekten
oynatılabilir bir dosyaya dönüşsün ("unpolyglot").

## Yaklaşım

### 1. Ayırma noktasının belirlenmesi — `detect_trailer.py`'nin yeniden kullanımı
Gün 4'te yazılan `detect_trailer.analyze()` fonksiyonu zaten görselin
gerçek bitiş offset'ini (`image_end_offset`) format-farkında bir şekilde
(PNG `IEND` chunk zinciri / JPEG marker taraması) hesaplıyor. `extract.py`
bu fonksiyonu doğrudan içe aktarıp çağırıyor — offset hesaplama mantığını
tekrar yazmak yerine tek kaynaktan besleniyor:

```python
from detect_trailer import analyze as analyze_trailer
...
trailer_info = analyze_trailer(path)
split_offset = trailer_info["image_end_offset"]
```

Gün 3'teki `make_polyglot.py` görseli ve videoyu **doğrudan concat**
ettiği için (`image_bytes + video_bytes`, ara bayt yok), ayırma noktası
olarak `image_end_offset`'in kendisi kullanıldı — `detect_trailer`'ın ayrı
raporladığı `hidden_video_offset` (imza taramasının bulduğu konum) değil.
İki değer bu projenin polyglot'larında pratikte örtüşür, ancak
`image_end_offset` format parsing'inden geldiği için daha güvenilir ayırma
noktasıdır; `hidden_video_offset` yalnızca *hangi imzanın bulunduğunu*
raporlamak içindir.

### 2. Polyglot olmayan dosyalarda güvenli reddetme
`detect_trailer_info["polyglot_status"]` `False` ise (gizli video imzası
yoksa) `extract()` hiçbir dosya yazmadan `ValueError` fırlatıyor;
`detect_trailer.py`'nin ürettiği `analysis_summary` mesajı hataya
zincirleniyor, böylece kullanıcı neden ayıklamanın reddedildiğini görüyor.

### 3. Çıktı dosyaları
- Video kısmı her zaman `<output-dir>/<stem>_extracted.mp4` olarak yazılıyor
  (varsayılan `output-dir`: `samples/extracted/`, zaten `.gitignore`'da).
- `--save-image` bayrağı verilirse, görsel kısmı da doğrulama amaçlı
  `<stem>_extracted_image.<png|jpg>` olarak ayrıca kaydediliyor (planın
  "opsiyonel" olarak işaretlediği alt görev).
- Sonuçta `size_match` alanıyla `dosya_boyutu == görsel_boyutu + video_boyutu`
  eşitliği doğrulanıp rapora ekleniyor.

## Script: `scripts/extract.py`

```
python scripts/extract.py --file <polyglot dosya>
python scripts/extract.py --file <polyglot dosya> --save-image --json
python scripts/extract.py --file <polyglot dosya> --output-dir <dizin>
```

Çıktı alanları: `file`, `file_size`, `image_format`, `split_offset`,
`image_size`, `video_size`, `size_match`, `extracted_video_path`,
`extracted_image_path`.

## Test Sonuçları

| Dosya | Ayırma offset'i | Görsel boyutu | Video boyutu | Toplam eşleşiyor mu? | `ffprobe` |
|---|---|---|---|---|---|
| `samples/polyglot_png.png` | 217 (`0xD9`) | 217 bayt | 3471 bayt | 3688 = 217+3471 ✅ | `probe_score=100`, h264/64x64/2s ✅ |
| `samples/polyglot_jpg.jpg` | 1371 (`0x55B`) | 1371 bayt | 3471 bayt | 4842 = 1371+3471 ✅ | `probe_score=100`, h264/64x64/2s ✅ |

Ayrıca `--save-image` ile ayıklanan görsel kısımları, `cmp` ile
orijinal kaynak dosyalarla (`samples/sample.png`, `samples/sample.jpg`)
**bayt-bayt aynı** çıktı (fark bulunamadı) — bu, ayırma noktasının
(`image_end_offset`) doğru hesaplandığını ve concatenation'ın kayıpsız
tersine çevrilebildiğini kanıtlıyor. `file` komutu da her iki ayıklanmış
görseli doğru formatında (`PNG image data`, `JPEG image data`) tanıdı.

Negatif test — temiz (video içermeyen) bir dosyada script hiçbir çıktı
dosyası üretmeden anlamlı bir hata ile reddediyor:

```
$ python scripts/extract.py --file samples/sample.jpg
Hata: 'samples/sample.jpg' bir polyglot dosya değil (gizli video imzası
bulunamadı): EOF sonrası fazladan veri yok, dosya temiz.
$ echo $?
1
```

Örnek insan-okur çıktı (`samples/polyglot_png.png`, `--save-image` olmadan):

```
Dosya:                 samples/polyglot_png.png
Dosya boyutu:          3688 bayt
Görsel formatı:        PNG
Ayırma offset'i:       217 (0xD9)
Görsel kısmı boyutu:   217 bayt
Video kısmı boyutu:    3471 bayt
Boyut tutarlılığı:     OK
Ayıklanan video:       samples/extracted/polyglot_png_extracted.mp4
```

## Kabul Kriterleri — Durum

- [x] Ayıklanan `.mp4` dosyası `ffprobe` ile hatasız açılıyor (her iki
      örnekte de `probe_score=100`, h264/64x64/2sn/20 kare) ve bir video
      player'da oynatılabilir durumda
- [x] Ayıklama işlemi sonrası orijinal polyglot dosyanın boyutu = ayıklanan
      görsel boyutu + ayıklanan video boyutu (her iki örnekte de doğrulandı)
- [x] (Ek doğrulama) Ayıklanan görsel kısmı orijinal kaynak görselle bayt-bayt
      aynı (`cmp` farksız)
- [x] (Ek doğrulama) Polyglot olmayan bir dosyada script dosya yazmadan
      anlamlı hata ile çıkıyor (exit code 1)

## Notlar / Riskler
- Yok (plan notu ile uyumlu). Ayırma mantığı, Gün 4'teki format-farkında
  offset hesaplamasına dayandığı için Gün 2'deki risklerin (gömülü EXIF
  thumbnail'inin sahte `EOI`'si, JPEG bayt-stuffing) `extract.py` seviyesinde
  tekrar ele alınmasına gerek kalmadı — tek bir yerde (`detect_trailer.py`)
  çözülmüş bir problem burada yeniden kullanıldı.
