#!/usr/bin/env python3
"""Görsel çözünürlüğü ve renk derinliğinden beklenen teorik dosya boyutunu
hesaplayıp gerçek dosya boyutuyla karşılaştırır.

Yöntem:
    - PNG: sıkıştırmasız ham boyut piksel sayısı × kanal × bit derinliğinden
      (+ satır başına 1 filtre baytı) hesaplanır, ardından tipik bir PNG
      sıkıştırma oranı varsayımıyla ("ham boyutun ~%20'si") ölçeklenir.
    - JPEG: sıkıştırmasız ham boyut piksel sayısı × kanal sayısından
      hesaplanır, ardından tipik bir JPEG sıkıştırma oranı varsayımıyla
      ("ham boyutun ~%10'u") ölçeklenir.
    Gerçek dosya boyutu bu teorik (beklenen) boyutu belirgin biçimde
    aşıyorsa (varsayılan eşik: %20), dosyaya normal piksel verisiyle
    açıklanamayan fazladan veri eklenmiş olabileceği "şüpheli" olarak
    işaretlenir.

Kullanım:
    python scripts/size_analysis.py --file samples/polyglot_png.png
    python scripts/size_analysis.py --file samples/sample.jpg --json
"""
import argparse
import json
import sys
from pathlib import Path

from detect_trailer import NO_LENGTH_MARKERS
from make_polyglot import detect_image_format

# Sıkıştırılmamış ham boyuta göre beklenen ortalama sıkıştırma oranları.
# İçeriğe göre değişkenlik gösterir (bkz. Notlar/Riskler); bunlar sadece
# kaba bir varsayılan tahmindir, tek başına kesin bir kanıt değildir.
PNG_EXPECTED_COMPRESSION_RATIO = 0.20   # ~5:1 — basit grafik/test içeriği varsayımı
JPEG_EXPECTED_COMPRESSION_RATIO = 0.10  # ~10:1 — tipik varsayılan kalite varsayımı

DEVIATION_THRESHOLD_PERCENT = 20.0

PNG_COLOR_TYPE_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
JPEG_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def read_png_dimensions(data: bytes) -> dict:
    if len(data) < 26 or data[12:16] != b"IHDR":
        raise ValueError("PNG IHDR chunk'ı bulunamadı (bozuk dosya)")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    bit_depth = data[24]
    color_type = data[25]
    if color_type not in PNG_COLOR_TYPE_CHANNELS:
        raise ValueError(f"Bilinmeyen PNG renk tipi: {color_type}")
    if width == 0 or height == 0:
        raise ValueError("PNG genişlik/yükseklik 0 olamaz (bozuk dosya)")
    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "channels": PNG_COLOR_TYPE_CHANNELS[color_type],
    }


def png_theoretical_raw_size(dims: dict) -> int:
    row_bits = dims["width"] * dims["channels"] * dims["bit_depth"]
    row_bytes = -(-row_bits // 8)  # ceil
    return dims["height"] * (1 + row_bytes)  # +1 satır başı filtre baytı


def read_jpeg_dimensions(data: bytes) -> dict:
    offset = 2  # SOI (FFD8) sonrası
    n = len(data)
    while offset + 1 < n:
        if data[offset] != 0xFF:
            raise ValueError(f"JPEG marker beklenirken 0x{data[offset]:02X} bulundu (offset {offset})")
        marker = data[offset + 1]
        offset += 2

        if marker in JPEG_SOF_MARKERS:
            if offset + 7 > n:
                raise ValueError("JPEG SOF segmenti eksik (bozuk dosya)")
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            channels = data[offset + 7]
            if width == 0 or height == 0:
                raise ValueError("JPEG genişlik/yükseklik 0 olamaz (bozuk dosya)")
            return {"width": width, "height": height, "channels": channels}

        if marker == 0xD9:  # EOI — SOF'a rastlanmadan dosya bitti
            break
        if marker in NO_LENGTH_MARKERS:
            continue

        length = int.from_bytes(data[offset:offset + 2], "big")
        offset += length

    raise ValueError("JPEG SOF marker'ı bulunamadı (boyut bilgisi okunamadı)")


def compute_theoretical_size(data: bytes, image_format: str) -> dict:
    if image_format == "png":
        dims = read_png_dimensions(data)
        raw_size = png_theoretical_raw_size(dims)
        ratio = PNG_EXPECTED_COMPRESSION_RATIO
    else:
        dims = read_jpeg_dimensions(data)
        raw_size = dims["width"] * dims["height"] * dims["channels"]
        ratio = JPEG_EXPECTED_COMPRESSION_RATIO

    return {
        "width": dims["width"],
        "height": dims["height"],
        "channels": dims["channels"],
        "raw_uncompressed_size": raw_size,
        "expected_compression_ratio": ratio,
        "theoretical_size": raw_size * ratio,
    }


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    file_size = len(data)

    image_format = detect_image_format(data)
    info = compute_theoretical_size(data, image_format)
    theoretical_size = info["theoretical_size"]

    deviation_percent = (file_size - theoretical_size) / theoretical_size * 100
    suspicious = deviation_percent > DEVIATION_THRESHOLD_PERCENT

    if suspicious:
        summary = (
            f"Gerçek boyut ({file_size} bayt), teorik boyutu (~{theoretical_size:.0f} bayt) "
            f"%{deviation_percent:.1f} aşıyor (eşik: %{DEVIATION_THRESHOLD_PERCENT:.0f}) — "
            f"piksel verisiyle açıklanamayan fazladan veri olabilir, şüpheli."
        )
    else:
        summary = (
            f"Gerçek boyut ({file_size} bayt), teorik boyut (~{theoretical_size:.0f} bayt) "
            f"ile uyumlu (sapma: %{deviation_percent:.1f}), normal aralıkta."
        )

    return {
        "file": str(path),
        "file_size": file_size,
        "image_format": image_format,
        "width": info["width"],
        "height": info["height"],
        "channels": info["channels"],
        "raw_uncompressed_size": info["raw_uncompressed_size"],
        "expected_compression_ratio": info["expected_compression_ratio"],
        "theoretical_size": round(theoretical_size),
        "deviation_percent": round(deviation_percent, 2),
        "threshold_percent": DEVIATION_THRESHOLD_PERCENT,
        "suspicious": suspicious,
        "analysis_summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Taranacak PNG/JPEG dosya yolu")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:                 {result['file']}")
    print(f"Dosya boyutu:          {result['file_size']} bayt")
    print(f"Görsel formatı:        {result['image_format'].upper()}")
    print(f"Boyutlar:              {result['width']}x{result['height']}, {result['channels']} kanal")
    print(f"Ham (sıkıştırmasız):   {result['raw_uncompressed_size']} bayt")
    print(f"Varsayılan sıkıştırma: %{result['expected_compression_ratio'] * 100:.0f}")
    print(f"Teorik boyut:          {result['theoretical_size']} bayt")
    print(f"Sapma:                 %{result['deviation_percent']:.1f} (eşik: %{result['threshold_percent']:.0f})")
    print(f"Şüpheli mi?            {'EVET' if result['suspicious'] else 'hayır'}")
    print(f"Özet:                  {result['analysis_summary']}")


def main() -> int:
    args = parse_args()
    try:
        result = analyze(args.file)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
