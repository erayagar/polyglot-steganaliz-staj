#!/usr/bin/env python3
"""Bir görselin piksellerinin en az anlamlı bitlerini (LSB) çıkarıp
görselleştirir; LSB steganografi izlerinin tespitine yardımcı olur.

Yöntem:
    Her kanalın (B, G, R) en az anlamlı biti (`piksel & 1`) alınıp 0/255
    aralığına ölçeklenerek bir "bit-plane" görüntüsü üretilir. Doğal/temiz
    bir görselde LSB düzlemi genellikle görsel içerikle bir miktar
    korelasyon gösterirken, LSB'lere rastgele veri gömülmüş (steganografi
    uygulanmış) bir görselde bu düzlem belirgin biçimde gürültülü/rastgele
    görünür.

    Bu script ayrıca `--make-demo-stego` ile, sabit tohumlu (`seed=42`)
    rastgele bitleri her piksel/kanalın LSB'ine yazarak klasik bir
    LSB-steganografi demo örneği üretebilir (karşılaştırma amaçlı).

Kullanım:
    python scripts/lsb_analysis.py --file samples/sample.png
    python scripts/lsb_analysis.py --file samples/polyglot_png.png --json
    python scripts/lsb_analysis.py --file samples/sample.png \
        --make-demo-stego samples/lsb_stego_sample.png
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

LSB_DEMO_SEED = 42


def load_image_array(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Görsel okunamadı (desteklenmeyen format veya bozuk dosya): {path}")
    return img


def extract_lsb_plane(img: np.ndarray) -> np.ndarray:
    """Her kanalın LSB'ini 0/255 aralığına ölçekleyip görselleştirilebilir bir görüntü döner."""
    return (img & 1) * 255


def lsb_one_ratio(img: np.ndarray) -> float:
    """Tüm piksel/kanallar arasında LSB'i 1 olanların oranı (0-1). Rastgele veride ~0.5 beklenir."""
    return float(np.mean(img & 1))


def embed_lsb_noise_demo(img: np.ndarray, seed: int = LSB_DEMO_SEED) -> np.ndarray:
    """Her piksel/kanalın LSB'ini sabit tohumlu rastgele bitlerle değiştirerek
    klasik bir LSB-steganografi gürültüsünü simüle eden demo görüntü üretir."""
    rng = np.random.RandomState(seed)
    random_bits = rng.randint(0, 2, size=img.shape, dtype=np.uint8)
    return (img & 0xFE) | random_bits


def analyze(path: Path, output_path: Path) -> dict:
    img = load_image_array(path)
    lsb_plane = extract_lsb_plane(img)
    ratio = lsb_one_ratio(img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), lsb_plane)

    deviation_from_random = abs(ratio - 0.5)
    summary = (
        f"LSB=1 oranı %{ratio * 100:.1f} (rastgele/gürültülü veri ~%50 gösterir); "
        f"%50'den sapma %{deviation_from_random * 100:.1f}."
    )

    return {
        "file": str(path),
        "width": img.shape[1],
        "height": img.shape[0],
        "channels": img.shape[2],
        "lsb_one_ratio": round(ratio, 4),
        "deviation_from_random": round(deviation_from_random, 4),
        "output": str(output_path),
        "analysis_summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Analiz edilecek (veya kaynak) görsel yolu")
    parser.add_argument(
        "--output", type=Path, default=None,
        help="LSB plane PNG çıktı yolu (varsayılan: docs/lsb-<dosya-adi>.png)",
    )
    parser.add_argument(
        "--make-demo-stego", type=Path, default=None, metavar="OUTPUT_PATH",
        help="Analiz yapmak yerine --file'ı kaynak alıp LSB-gürültülü demo dosya üretir",
    )
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:              {result['file']}")
    print(f"Boyutlar:           {result['width']}x{result['height']}, {result['channels']} kanal")
    print(f"LSB=1 oranı:        %{result['lsb_one_ratio'] * 100:.1f}")
    print(f"%50'den sapma:      %{result['deviation_from_random'] * 100:.1f}")
    print(f"LSB plane kaydedildi: {result['output']}")
    print(f"Özet:               {result['analysis_summary']}")


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        print(f"Hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1

    if args.make_demo_stego is not None:
        try:
            img = load_image_array(args.file)
        except ValueError as exc:
            print(f"Hata: {exc}", file=sys.stderr)
            return 1
        stego = embed_lsb_noise_demo(img)
        args.make_demo_stego.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.make_demo_stego), stego)
        print(f"LSB-gürültülü demo dosya üretildi: {args.make_demo_stego}")
        return 0

    safe_name = args.file.name.replace(".", "_")
    output_path = args.output or Path("docs") / f"lsb-{safe_name}.png"

    try:
        result = analyze(args.file, output_path)
    except ValueError as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
