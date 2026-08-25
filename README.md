# Polyglot / Steganaliz Servisi

X (Twitter) gibi platformlarda paylaşılan görsel dosyaların arkasına gizlenmiş video/veri (polyglot dosya) tespiti yapan, uçtan uca bir siber güvenlik + bilgisayar görüsü + web servisi projesi.

Bu proje bir **20 günlük staj programı** kapsamında geliştirilmektedir. Günlük plan ve ilerleme takibi için: [PLAN.md](./PLAN.md)

> Bu proje yalnızca eğitim ve savunma (defensive security) amaçlıdır. Gerçek kullanıcı verisi toplanmaz veya kazınmaz; tüm test dosyaları sentetik olarak üretilir.

## Teknoloji Yığını
- **Backend:** Python 3.11+, FastAPI, Pydantic, Uvicorn
- **Görüntü/Video İşleme:** OpenCV, Pillow, NumPy, ffmpeg/ffprobe
- **Frontend:** HTML5 / CSS3 / Vanilla JS
- **Analiz:** Shannon entropy, LSB/DCT gürültü analizi, dosya trailer (EOF ötesi) taraması

## Proje Yapısı
```
polyglot-steganaliz-staj/
├── PLAN.md          # 20 günlük detaylı çalışma planı
├── backend/         # FastAPI servisi
├── frontend/        # Web dashboard
├── scripts/         # Polyglot üretici ve analiz script'leri
├── samples/         # Sentetik test dosyaları (git'e dahil değil)
└── docs/            # Format notları, test sonuçları, staj raporu
```

## Kurulum
> Bu bölüm Hafta 1 ilerledikçe doldurulacak.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Kullanım
> Bu bölüm Hafta 3-4 ilerledikçe doldurulacak (API çalıştırma, endpoint kullanımı, frontend erişimi).

## Lisans / Etik Not
Bu proje yalnızca eğitim ve savunma amaçlı geliştirilmiştir. Herhangi bir platformdan izinsiz veri kazıma (scraping) veya gerçek kullanıcı verisiyle test yapılmaz.
