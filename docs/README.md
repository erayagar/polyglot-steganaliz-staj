# `docs/` İndeksi

Bu klasör üç tür içerik barındırır: **kalıcı referans dokümanları**,
**günlük/haftalık ilerleme raporları** ve raporların içinden göreli yolla
referans verilen **üretilmiş analiz görselleri**. Aşağıdaki liste
klasördeki dosyaları bu üç kategoriye göre gruplar; dosyalar taşınmadı
(raporlar görselleri `docs/` içinde göreli dosya adıyla referans ettiği
için taşımak linkleri kırar).

## Referans Dokümanları
- [`format-notlari.md`](./format-notlari.md) — PNG/JPEG/MP4 binary format
  yapısı: imza (magic bytes) ve sonlandırıcı işaret tablosu (Gün 2).
- [`test-sonuclari.md`](./test-sonuclari.md) — farklı senaryolarda
  (PNG/JPEG polyglot, yeniden sıkıştırma, temiz dosya, uçtan uca web
  testleri) tespit başarımı tablosu (Gün 10 + Gün 18).
- [`staj-raporu.md`](./staj-raporu.md) / [.pdf](./staj-raporu.pdf) — 20
  günlük stajın final raporu: özet, yöntem, karşılaşılan zorluklar,
  sonuçlar (Gün 20).

## Günlük Raporlar (`gunN-*`)
Her gün için Hedef/Yaklaşım/Test Sonuçları/Kabul Kriterleri-Durum/Notlar
bölümleriyle yazılmış rapor. `.md` ana kaynak, `.pdf` aynı içeriğin
sunulabilir kopyasıdır (Gün 1 ve Gün 2 yalnızca `.pdf` olarak mevcut).

| Gün | Konu | Rapor |
|---|---|---|
| 1 | Ortam kurulumu | [gun1-kurulum-notlari.pdf](./gun1-kurulum-notlari.pdf) |
| 2 | Format analizi (binary düzey) | [gun2-format-analizi-raporu.pdf](./gun2-format-analizi-raporu.pdf) |
| 3 | Polyglot üretici script | [gun3-polyglot-uretici-raporu.md](./gun3-polyglot-uretici-raporu.md) |
| 4 | EOF ötesi trailer tespiti | [gun4-trailer-tespit-raporu.md](./gun4-trailer-tespit-raporu.md) |
| 5 | Shannon entropy analizi | [gun5-entropy-analizi-raporu.md](./gun5-entropy-analizi-raporu.md) |
| 6 | Teorik/gerçek boyut sapması | [gun6-boyut-sapma-analizi-raporu.md](./gun6-boyut-sapma-analizi-raporu.md) |
| 7 | LSB / DCT gürültü analizi | [gun7-lsb-dct-analizi-raporu.md](./gun7-lsb-dct-analizi-raporu.md) |
| 8 | Extraction (unpolyglot) | [gun8-extraction-raporu.md](./gun8-extraction-raporu.md) |
| 9 | Video meta verisi | [gun9-video-metadata-raporu.md](./gun9-video-metadata-raporu.md) |
| 10 | Senaryo bazlı test başarımı | [gun10-test-senaryolari-raporu.md](./gun10-test-senaryolari-raporu.md) |
| 11 | FastAPI iskeleti | [gun11-fastapi-iskelet-raporu.md](./gun11-fastapi-iskelet-raporu.md) |
| 12 | Dosya yükleme endpoint'i | [gun12-dosya-yukleme-endpoint-raporu.md](./gun12-dosya-yukleme-endpoint-raporu.md) |
| 13 | Pipeline entegrasyonu | [gun13-pipeline-entegrasyonu-raporu.md](./gun13-pipeline-entegrasyonu-raporu.md) |
| 14 | JSON yanıt şeması / threat_score | [gun14-json-yanit-semasi-raporu.md](./gun14-json-yanit-semasi-raporu.md) |
| 15 | Swagger testleri ve hata yönetimi | [gun15-swagger-hata-yonetimi-raporu.md](./gun15-swagger-hata-yonetimi-raporu.md) |
| 16 | Sürükle-bırak arayüzü | [gun16-surukle-birak-arayuz-raporu.md](./gun16-surukle-birak-arayuz-raporu.md) |
| 17 | Frontend-backend entegrasyonu | [gun17-frontend-backend-entegrasyonu-raporu.md](./gun17-frontend-backend-entegrasyonu-raporu.md) |
| 18 | Uçtan uca doğrulama testleri | [gun18-uctan-uca-dogrulama-raporu.md](./gun18-uctan-uca-dogrulama-raporu.md) |
| 19 | Dokümantasyon ve depo düzenleme | [gun19-dokumantasyon-repo-raporu.md](./gun19-dokumantasyon-repo-raporu.md) / [.pdf](./gun19-dokumantasyon-repo-raporu.pdf) |
| 20 | Sunum, demo provası ve staj raporu teslimi | [gun20-demo-ve-kapanis-raporu.md](./gun20-demo-ve-kapanis-raporu.md) / [.pdf](./gun20-demo-ve-kapanis-raporu.pdf) |

## Haftalık Özet Raporlar
- [`hafta1-raporu.md`](./hafta1-raporu.md) — Hafta 1 (Gün 1-5): dosya
  format mimarisi, polyglot üretimi, trailer/entropy analizi.
- [`hafta2-raporu.md`](./hafta2-raporu.md) — Hafta 2 (Gün 6-10):
  steganaliz motoru, extraction, video meta verisi, senaryo testleri.
- [`hafta3-raporu.md`](./hafta3-raporu.md) — Hafta 3 (Gün 11-15): FastAPI
  REST servisi, pipeline entegrasyonu, `threat_score` şeması, hata yönetimi.
- [`hafta4-raporu.md`](./hafta4-raporu.md) — Hafta 4 (Gün 16-20): web
  dashboard, uçtan uca doğrulama, dokümantasyon, staj final raporu.

## Üretilmiş Analiz Görselleri
Günlük raporların içinden göreli dosya adıyla (`![...](dosya.png)`)
referans verilen, `scripts/entropy.py` / `scripts/lsb_analysis.py` /
`scripts/dct_analysis.py` tarafından üretilmiş grafik/ısı haritası
çıktıları:

| Görsel deseni | Kaynak script | Kullanıldığı rapor(lar) |
|---|---|---|
| `entropy-*.png` | `scripts/entropy.py` | gun5, hafta1 |
| `gun10-entropy-*.png` | `scripts/entropy.py` (Gün 10 test matrisi) | gun10, hafta2 |
| `lsb-*.png` | `scripts/lsb_analysis.py` | gun7, hafta2 |
| `dct-*.png` | `scripts/dct_analysis.py` | gun7 |

## Diğer Dokümantasyon (proje kökünde)
- [`../PLAN.md`](../PLAN.md) — 20 günlük plan, kabul kriterleri, ilerleme durumu.
- [`../README.md`](../README.md) — kurulum, kullanım ve mimari anlatımı.
