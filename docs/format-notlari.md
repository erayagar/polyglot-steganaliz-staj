# Format Notları — PNG, JPEG ve MP4 Binary Yapısı

Bu doküman, Gün 2 kapsamında PNG, JPEG ve MP4 dosya formatlarının iç yapısının
(chunk/marker/atom) hex düzeyinde incelenmesiyle oluşturulmuştur. Örnekler
`samples/sample.png`, `samples/sample.jpg`, `samples/sample.mp4` dosyalarıdır
(sentetik olarak `Pillow` ve `ffmpeg` ile üretilmiştir).

---

## 1. Özet Tablo — İmza (Magic Bytes) ve Sonlandırıcı İşaretler

| Format | Başlangıç İmzası (Magic Bytes) | Dosya Sonu / Bitiş İşareti |
|---|---|---|
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `IEND` chunk'ı: uzunluk `00 00 00 00` + tip `49 45 4E 44` + sabit CRC `AE 42 60 82` |
| JPEG | `FF D8` (SOI) | `FF D9` (EOI) |
| MP4 | Byte 0-3 dosya boyutuna göre değişir; byte 4-7 sabit `66 74 79 70` (`ftyp`) | Sabit bir bitiş imzası yok — yapı, box (atom) uzunluk alanlarıyla belirlenir; son box dosyanın sonunda biter (`mdat` veya `moov` olabilir) |

---

## 2. PNG

### Yapı
PNG dosyası 8 baytlık sabit bir imza ile başlar, ardından sırayla
**length(4) + type(4) + data(length) + CRC(4)** biçiminde "chunk"lardan oluşur.

| Chunk | Anlamı |
|---|---|
| `IHDR` | Image Header — genişlik, yükseklik, bit derinliği, renk tipi vb. (her PNG'de ilk chunk) |
| `IDAT` | Image Data — sıkıştırılmış (zlib/DEFLATE) piksel verisi, birden fazla olabilir |
| `IEND` | Image End — veri içermez (length=0), dosyanın bittiğini işaret eder |

### `samples/sample.png` içinde bulunan offsetler (dosya boyutu: 217 bayt)

| Alan | Offset (hex) | Offset (dec) | Değer |
|---|---|---|---|
| PNG imzası | `0x00`–`0x07` | 0–7 | `89 50 4E 47 0D 0A 1A 0A` |
| `IHDR` chunk başlangıcı (length alanı) | `0x08` | 8 | length `00 00 00 0D` (13 bayt veri) |
| `IHDR` type alanı | `0x0C` | 12 | `49 48 44 52` (`IHDR`) |
| `IDAT` chunk başlangıcı (length alanı) | `0x21` | 33 | length `00 00 00 A0` (160 bayt veri) |
| `IDAT` type alanı | `0x25` | 37 | `49 44 41 54` (`IDAT`) |
| **`IEND` chunk başlangıcı (length alanı)** | **`0xCD`** | **205** | length `00 00 00 00` |
| **`IEND` type alanı** | **`0xD1`** | **209** | `49 45 4E 44` (`IEND`) |
| Dosya sonu (IEND CRC'nin son baytı) | `0xD8` | 216 | `AE 42 60 82` (son 4 bayt) |

`xxd samples/sample.png` ile alınan tam döküm:

```
00000000: 8950 4e47 0d0a 1a0a 0000 000d 4948 4452  .PNG........IHDR
00000010: 0000 0040 0000 0040 0802 0000 0025 0be6  ...@...@.....%..
00000020: 8900 0000 a049 4441 5478 9ced d7c1 09c3  .....IDATx......
...
000000c0: bb1f f0ab 0fe0 fe40 9979 33c3 1800 0000  .......@.y3.....
000000d0: 0049 454e 44ae 4260 82                   .IEND.B`.
```

---

## 3. JPEG

### Yapı
JPEG dosyası, her biri `FF xx` biçiminde 2 baytlık bir marker ile başlayan
segmentlerden oluşur. Çoğu marker'ı 2 baytlık bir uzunluk alanı takip eder
(SOI ve EOI hariç).

| Marker | Bayt | Anlamı |
|---|---|---|
| `SOI` | `FF D8` | Start of Image — dosyanın ilk iki baytı |
| `APPn` | `FF E0`–`FF EF` | Application segment (örn. `APP0`=`FF E0` → JFIF meta verisi) |
| `DQT` | `FF DB` | Define Quantization Table |
| `SOF0` | `FF C0` | Start of Frame (baseline DCT) |
| `SOS` | `FF DA` | Start of Scan — sıkıştırılmış görüntü verisi buradan sonra başlar |
| `EOI` | `FF D9` | End of Image — dosyanın bittiğini işaret eder |

### `samples/sample.jpg` içinde bulunan offsetler (dosya boyutu: 1371 bayt)

| Alan | Offset (hex) | Offset (dec) | Değer |
|---|---|---|---|
| `SOI` | `0x00`–`0x01` | 0–1 | `FF D8` |
| `APP0` (JFIF) marker | `0x02`–`0x03` | 2–3 | `FF E0` (uzunluk `00 10`, ardından `JFIF\0`) |
| `DQT` marker | `0x14`–`0x15` | 20–21 | `FF DB` |
| `SOF0` marker | `0x9E`–`0x9F` | 158–159 | `FF C0` |
| **`EOI`** | **`0x559`–`0x55A`** | **1369–1370** | `FF D9` |

`xxd samples/sample.jpg` başlangıç ve bitiş dökümü:

```
00000000: ffd8 ffe0 0010 4a46 4946 0001 0100 0001  ......JFIF......
00000010: 0001 0000 ffdb 0043 0005 0304 0404 0305  .......C........
...
00000540: 2f9d efd2 c1ff 0024 4ffd 3ef6 dff6 e5b9  /......$O.>.....
00000550: 3ff0 2bdf 9bca d6eb 73ff d9              ?.+.....s..
```

Son iki bayt (`ff d9`) dosyanın son baytları — yani bu temiz JPEG'de `EOI`
tam olarak dosya sonunda (trailer yok).

---

## 4. MP4 (ISO Base Media File Format)

### Yapı
MP4, PNG/JPEG'in aksine tek bir sabit sihirli bayt dizisiyle başlamaz;
bunun yerine **box (atom)** adı verilen, `size(4) + type(4) + data(size-8)`
biçiminde iç içe geçebilen bloklardan oluşur. İlk box neredeyse her zaman
`ftyp`'tir, bu yüzden dosyanın 4-7. baytları (`ftyp`'in tip alanı) pratikte
"MP4 imzası" olarak kullanılır.

| Atom | Anlamı |
|---|---|
| `ftyp` | File Type — dosya markası/uyumluluk bilgisi (ör. `isom`, `mp42`) |
| `free` | Kullanılmayan/dolgu alanı (opsiyonel) |
| `mdat` | Media Data — asıl ses/video baytları |
| `moov` | Movie — codec, süre, track bilgisi (metadata); `mdat`'ten önce veya sonra olabilir (encoder'a göre değişir) |

### `samples/sample.mp4` içinde bulunan offsetler (dosya boyutu: 3471 bayt)

| Atom | Offset (hex) | Offset (dec) | Box boyutu |
|---|---|---|---|
| `ftyp` | `0x00` (size), `0x04` (type) | 0, 4 | 32 bayt |
| `free` | `0x20` (size), `0x24` (type) | 32, 36 | 8 bayt |
| `mdat` | `0x28` (size), `0x2C` (type) | 40, 44 | 2374 bayt |
| `moov` | `0x96E` (size), `0x972` (type) | 2414, 2418 | dosya sonuna kadar |

`xxd samples/sample.mp4` başlangıç dökümü:

```
00000000: 0000 0020 6674 7970 6973 6f6d 0000 0200  ... ftypisom....
00000010: 6973 6f6d 6973 6f32 6176 6331 6d70 3431  isomiso2avc1mp41
00000020: 0000 0008 6672 6565 0000 0946 6d64 6174  ....free...Fmdat
```

Bu örnekte `moov`, `mdat`'ten **sonra** geliyor (faststart olmayan bir
mux sırası) — bu, MP4 için genel/sabit bir kural değildir, encoder'a göre
değişebilir (bkz. Notlar).

---

## 5. Notlar / Riskler

- **MP4 atom sırası sabit değildir.** `ftyp` neredeyse her zaman ilk box'tır,
  ancak `moov` bazı encoder'larda (`faststart`) `mdat`'ten önce, bazılarında
  (bizim örneğimizde olduğu gibi) sonra gelir. Trailer/polyglot tespitinde
  yalnızca `ftyp` konumuna güvenilmemeli, tüm bilinen atom imzaları
  (`ftyp`, `moov`, `mdat`, `free`) taranmalıdır.
- **JPEG'de EOI sonrası veri her zaman "gizli veri" anlamına gelmez.**
  Bazı uygulamalar EXIF/thumbnail veya dolgu baytlarını EOI'den sonra
  bırakabilir. Gün 4'te trailer tespiti yaparken minimum imza uzunluğu/boyut
  eşiği kullanılmalı.
- **PNG'de `IEND` chunk'ının CRC'si sabittir** (`AE 42 60 82`), çünkü
  chunk verisi boştur (uzunluk=0). Bu, `IEND` sonrası trailer aramak için
  güvenilir bir referans noktasıdır.
