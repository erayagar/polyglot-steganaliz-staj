# Gün 14 — JSON Yanıt Şemasının Tasarlanması

## Hedef
`AnalyzeResponse` şemasını plan'ın istediği dört alanla (`polyglot_status`,
`threat_score`, `extracted_video_url`, `analysis_summary`) kesinleştirmek;
`threat_score`i sinyallerin ağırlıklı birleşimiyle hesaplamak;
`analysis_summary`i tespit edilen video bilgisiyle dinamik üretmek.

## Yaklaşım

### 1. `AnalyzeResponse` alanlarının kesinleştirilmesi
Gün 13'te `threat_score` ve `analysis_summary` opsiyonel/placeholder
bırakılmıştı. Bu günle birlikte her istek için ikisi de her zaman
hesaplandığından `backend/app/models.py`'de zorunlu alanlara çevrildi:
`threat_score: int` (varsayılansız) ve `analysis_summary: str`
(varsayılansız). `extracted_video_url: str | None = None` polyglot
olmayan dosyalarda gerçekten `None` döneceği için opsiyonel kaldı.

### 2. `threat_score` ağırlıklı hesabı
`backend/app/pipeline.py`'ye `compute_threat_score(result)` eklendi.
Üç sinyal ağırlıklı olarak toplanıyor (toplam üst sınır 100'e kırpılır):

| Sinyal | Kaynak | Ağırlık | Ölçekleme |
|---|---|---|---|
| Trailer tespiti (`polyglot_status`) | Gün 4 | 60 | var/yok (0 veya 60) |
| Entropy farkı (`entropy_delta`) | Gün 5 | 25 | `delta / 3.0 bit`, 1.0'de kırpılır |
| Boyut sapması (`deviation_percent`) | Gün 6 | 15 | `sapma% / 100`, 1.0'de kırpılır |

Ağırlıkların dağılımı Gün 6/7 raporlarındaki disipline dayanıyor: trailer
tespiti en az yanlış-pozitif üreten ve en güçlü sinyal olduğu için baskın
ağırlığı (60/100) alıyor; entropy ve boyut sapması "tek başına kesin kanıt
değil, tamamlayıcı sinyal" olarak konumlandırıldığından (Gün 6 ve Gün 7
raporlarının Notlar bölümü) daha düşük ağırlıklarla (25 ve 15) katkı
sağlıyor — trailer tespiti olmadan yalnızca bu iki sinyalle skor en fazla
40'a ulaşabiliyor, 100'e değil.

Entropy ölçek sabiti (3.0 bit/bayt) ve boyut ölçek sabiti (%100 sapma)
kaba varsayılan eşiklerdir; gerçek veri setiyle kalibrasyon bu projenin
kapsamı dışında tutuldu (Gün 6'daki "%20 eşiği de bir varsayım" notuyla
tutarlı).

### 3. `analysis_summary` dinamik üretimi
`build_analysis_summary(result, threat_score)` eklendi:
- Polyglot değilse: Gün 4'ün trailer özetine `threat_score` ekleniyor.
- Polyglot ise: tespit edilen imza + offset + `threat_score` ile başlıyor;
  Gün 9'un `video_metadata` sonucu mevcutsa (`ffprobe`/OpenCV başarılıysa)
  çözünürlük, süre ve codec bilgisini de cümleye ekliyor. `video_metadata`
  `None` dönerse (örn. ffprobe/OpenCV video akışını okuyamazsa) bu ek cümle
  atlanıyor — özet yine de temel bilgiyi (imza, offset, skor) içermeye
  devam ediyor.

### 4. Endpoint'in bağlanması
`backend/app/main.py`'de `pipeline.run_pipeline` sonucundan sonra
`threat_score = pipeline.compute_threat_score(result)` hesaplanıp hem
`AnalyzeResponse.threat_score`e hem `build_analysis_summary`e parametre
olarak veriliyor.

## Dosyalar
```
backend/app/models.py      # threat_score/analysis_summary zorunlu alan oldu
backend/app/pipeline.py    # compute_threat_score(), build_analysis_summary()
backend/app/main.py        # endpoint threat_score hesabını kullanıyor
```

## Test Sonuçları
`uvicorn app.main:app --port 8014` ile başlatılıp `curl` ile test edildi.

| Dosya | `polyglot_status` | `threat_score` | `extracted_video_url` |
|---|---|---|---|
| `samples/sample.png` (temiz) | `false` | `0` | `null` |
| `samples/sample.jpg` (temiz) | `false` | `2` | `null` |
| `samples/polyglot_png.png` | `true` | `76` | `/media/<uuid>_extracted.mp4` |
| `samples/polyglot_jpg.jpg` | `true` | `85` | `/media/<uuid>_extracted.mp4` |
| `samples/test_matrix/recompressed_pre_png.png` (yeniden sıkıştırılmış polyglot) | `true` | `75` | `/media/<uuid>_extracted.mp4` |

```
$ curl -s -F "file=@samples/polyglot_png.png;type=image/png" http://127.0.0.1:8014/api/v1/analyze
{
  "polyglot_status": true,
  "threat_score": 76,
  "extracted_video_url": "/media/81c78d83ac5d4b9289d8bafbf44fdf7f_extracted.mp4",
  "analysis_summary": "Görsele gizlenmiş video tespit edildi: 'mp4/ftyp' imzası offset 217 konumunda bulundu (threat_score=76). Ayıklanan video: 64x64, 2.0 sn, codec=h264."
}

$ curl -s -F "file=@samples/sample.png;type=image/png" http://127.0.0.1:8014/api/v1/analyze
{
  "polyglot_status": false,
  "threat_score": 0,
  "extracted_video_url": null,
  "analysis_summary": "EOF sonrası fazladan veri yok, dosya temiz. (threat_score=0)"
}
```

Gün 15'e kalan hata senaryoları (desteklenmeyen tür → 400, `/docs`) bu
değişiklikten etkilenmediği doğrulandı; Gün 12/13 davranışları korunuyor.

## Kabul Kriterleri — Durum
- [x] API yanıtı örnek bir polyglot dosya için `polyglot_status: true`,
      anlamlı bir `threat_score` (76-85 aralığında, temiz dosyalardan
      belirgin şekilde yüksek) ve dolu bir `extracted_video_url`
      döndürüyor
- [x] Temiz bir dosya için `polyglot_status: false` ve düşük `threat_score`
      (0-2) döndürüyor

## Notlar / Riskler
- Ağırlıklar ve ölçek sabitleri (3.0 bit entropy farkı, %100 boyut sapması)
  sentetik test verisiyle makul sonuç verecek şekilde seçildi, ama
  kalibre edilmiş/istatistiksel değil; gerçek/çeşitli veri setiyle
  ayarlanması gerekebilir — bu, projenin "eğitim amaçlı demo" kapsamında
  kabul edilebilir bulundu (Gün 6 raporundaki benzer notla tutarlı).
- `video_metadata` adımı başarısız olursa (`ffprobe`/OpenCV video akışını
  okuyamazsa) `analysis_summary` yalnızca temel bilgiyi içerir; bu durum
  Gün 15'in hata yönetimi kapsamında ayrıca ele alınabilir ama şu an bir
  hataya değil, eksik bir cümleye yol açıyor (zarif bozulma).
