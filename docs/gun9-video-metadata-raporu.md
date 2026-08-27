# Gün 9 — Ayıklanan Video Meta Verisi Analizi

## Hedef
Gün 8'de ayıklanan (`extract.py` çıktısı) gizli MP4 videosunun kare sayısı,
süresi, çözünürlüğü ve codec bilgisinin çıkarılması; birincil yöntem
`ffprobe`, `ffprobe` yoksa/başarısız olursa OpenCV `cv2.VideoCapture` ile
yedek okuma yapılması.

## Yaklaşım

### 1. Birincil yöntem — `ffprobe -print_format json`
`_probe_ffprobe()`, `shutil.which("ffprobe")` ile ikilinin varlığını
kontrol edip `ffprobe -v error -print_format json -show_format
-show_streams <dosya>` komutunu çalıştırıyor. Çıktıdaki `streams`
listesinden `codec_type == "video"` olan ilk akış seçiliyor (ses akışı
varsa göz ardı ediliyor). Süre önce akış seviyesinden (`duration`),
yoksa `format.duration`'dan alınıyor; FPS `r_frame_rate` (`num/den`
string'i) üzerinden hesaplanıyor; `nb_frames` yoksa `fps × duration`
ile yaklaşık kare sayısı türetiliyor.

### 2. Yedek yöntem — OpenCV `cv2.VideoCapture`
`_probe_opencv()`, `cap.get(cv2.CAP_PROP_FRAME_COUNT/FPS/FRAME_WIDTH/
FRAME_HEIGHT/FOURCC)` ile aynı alanları bağımsız olarak okuyor. `FOURCC`
sayısal kodu 4 karaktere çözülüp codec adı olarak raporlanıyor.
`cap.isOpened()` `False` dönerse (dosya video olarak açılamıyorsa)
fonksiyon `None` döndürüp çağıran tarafın diğer yönteme düşmesini
sağlıyor.

### 3. Birleştirme mantığı
`get_metadata()` her iki yöntemi de çalıştırıyor (ffprobe kuruluysa her
zaman ikisi de çalışır, böylece sonuçlar birbirine karşı doğrulanabilir).
`ffprobe` sonucu varsa birincil (`primary`) kaynak olarak kullanılıyor;
yoksa OpenCV sonucu birincil oluyor ve `used_opencv_fallback: true`
işaretleniyor. Nihai sözlükte hem birleşik/birincil alanlar (`frame_count`,
`duration_seconds`, `width`, `height`, `fps`, `codec`,
`container_format`) hem de ham `ffprobe_result` / `opencv_result`
alt-sözlükleri ayrı ayrı korunuyor — böylece iki yöntem arasında sapma
olursa (örn. konteyner bozuksa) fark görülebiliyor.

İkisi de video olarak okuyamazsa (`ffprobe_result is None and
opencv_result is None`) `ValueError` fırlatılıyor; dosya bulunamazsa
`FileNotFoundError`.

## Script: `scripts/video_metadata.py`

```
python scripts/video_metadata.py --file <video dosyası>
python scripts/video_metadata.py --file <video dosyası> --json
```

Çıktı alanları: `file`, `file_size`, `frame_count`, `duration_seconds`,
`width`, `height`, `fps`, `codec`, `container_format`, `primary_source`,
`used_opencv_fallback`, `ffprobe_result`, `opencv_result`.

## Test Sonuçları

Gün 8'de ayıklanan iki örnek video üzerinde çalıştırıldı — ffprobe ve
OpenCV sonuçları tam olarak örtüştü:

| Dosya | Kare sayısı | Süre | Çözünürlük | FPS | Codec | ffprobe = OpenCV? |
|---|---|---|---|---|---|---|
| `samples/extracted/polyglot_png_extracted.mp4` | 20 | 2.0 sn | 64x64 | 10.0 | h264 | ✅ birebir aynı |
| `samples/extracted/polyglot_jpg_extracted.mp4` | 20 | 2.0 sn | 64x64 | 10.0 | h264 | ✅ birebir aynı |

Örnek insan-okur çıktı:

```
$ python scripts/video_metadata.py --file samples/extracted/polyglot_png_extracted.mp4
Dosya:                 samples/extracted/polyglot_png_extracted.mp4
Dosya boyutu:          3471 bayt
Kare sayısı:           20
Süre:                  2.0 sn
Çözünürlük:            64x64
FPS:                   10.0
Codec:                 h264
Konteyner formatı:     mov,mp4,m4a,3gp,3g2,mj2
Birincil kaynak:       ffprobe (ffprobe)
```

Negatif test — var olmayan dosya:

```
$ python scripts/video_metadata.py --file samples/nope.mp4
Hata: Dosya bulunamadı: samples/nope.mp4
$ echo $?
1
```

Not: Ayıklanmış görsel kısmı (`polyglot_png_extracted_image.png`) script'e
verildiğinde `ffprobe` bunu da tek kareli bir "video" akışı (`codec:
png`, `frame_count: None`, `fps: 25.0` — ffprobe'un görsellere verdiği
varsayılan değer) olarak okuyor; bu, ffprobe'un standart davranışı
(görselleri tek kareli video olarak ele alması) olup script'in bir hatası
değil — script'in görevi zaten yalnızca Gün 8'de *doğrulanmış* bir video
dosyasının meta verisini okumak, dosyanın "gerçek bir video mu"
olduğunu ayrıca doğrulamak değil (bu iş Gün 4/8'de `detect_trailer.py`
ile zaten yapılıyor).

## Kabul Kriterleri — Durum

- [x] Ayıklanan örnek videolar için kare sayısı, süre (saniye),
      çözünürlük ve codec adı doğru şekilde raporlanıyor (her iki örnekte
      de ffprobe ve OpenCV sonuçları birbiriyle örtüşüyor)

## Notlar / Riskler
- Yok (plan notu ile uyumlu). `ffprobe` bulunamadığı ortamlarda script
  otomatik olarak OpenCV'ye düşüyor; her iki araç da yoksa/dosya video
  olarak açılamıyorsa anlamlı bir `ValueError` ile hata veriyor.
