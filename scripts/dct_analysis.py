#!/usr/bin/env python3
"""Bir görseli 8x8 (veya verilen boyutta) bloklara bölüp her blok için
OpenCV `cv2.dct` ile DCT (Ayrık Kosinüs Dönüşümü) katsayılarını hesaplar
ve blok bazlı yüksek frekans enerjisini bir ısı haritası olarak
görselleştirir.

Yöntem:
    Görsel gri tonlamaya çevrilir, `block_size x block_size` bloklara
    ayrılır (taşan kenar piksel'ler atılır). Her blokta `cv2.dct()`
    uygulanır; blok içindeki düşük frekans köşesi (sol üst 2x2, DC dahil)
    dışındaki katsayıların mutlak değer toplamı "yüksek frekans enerjisi"
    olarak alınır. Doğal/temiz bir görselde blok enerjisi görsel içeriğe
    (kenar/detay yoğunluğuna) göre değişkenlik gösterirken, LSB'lere
    rastgele veri gömülmüş bir görselde yüksek frekans enerjisi tüm
    bloklarda belirgin biçimde ve tekdüze (uniform) şekilde yükselir —
    çünkü rastgele bit gürültüsü frekans alanında geniş bantlı enerji
    üretir.

Kullanım:
    python scripts/dct_analysis.py --file samples/sample.png
    python scripts/dct_analysis.py --file samples/polyglot_png.png --json
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_BLOCK_SIZE = 8
LOW_FREQ_CORNER = 2  # sol üst LOW_FREQ_CORNER x LOW_FREQ_CORNER katsayı = düşük frekans
FLAT_ENERGY_THRESHOLD = 1.0  # bu değerin altı "gözle görülür yüksek frekans yok" sayılır
UNIFORM_RELATIVE_STD_THRESHOLD = 0.5  # std/ortalama bu değerin altındaysa "tekdüze" (gürültü benzeri)


def load_grayscale(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Görsel okunamadı (desteklenmeyen format veya bozuk dosya): {path}")
    return img


def compute_block_high_freq_energy(gray: np.ndarray, block_size: int) -> np.ndarray:
    """Gri tonlamalı görüntüyü bloklara ayırıp her blok için yüksek frekans
    DCT enerjisini hesaplar; sonuç blok-çözünürlüğünde bir 2B dizi."""
    h, w = gray.shape
    rows = h // block_size
    cols = w // block_size
    if rows == 0 or cols == 0:
        raise ValueError(f"Görsel ({w}x{h}) blok boyutundan ({block_size}) küçük")

    cropped = gray[:rows * block_size, :cols * block_size].astype(np.float32)
    energy_map = np.zeros((rows, cols), dtype=np.float64)

    for r in range(rows):
        for c in range(cols):
            block = cropped[r * block_size:(r + 1) * block_size, c * block_size:(c + 1) * block_size]
            coeffs = cv2.dct(block)
            total_energy = np.sum(np.abs(coeffs))
            low_freq_energy = np.sum(np.abs(coeffs[:LOW_FREQ_CORNER, :LOW_FREQ_CORNER]))
            energy_map[r, c] = total_energy - low_freq_energy

    return energy_map


def plot_energy_map(energy_map: np.ndarray, title: str, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(energy_map, cmap="inferno", interpolation="nearest")
    ax.set_xlabel("Blok sütunu")
    ax.set_ylabel("Blok satırı")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Yüksek frekans DCT enerjisi")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def analyze(path: Path, block_size: int, output_path: Path) -> dict:
    gray = load_grayscale(path)
    energy_map = compute_block_high_freq_energy(gray, block_size)

    title = f"Blok Bazlı Yüksek Frekans DCT Enerjisi — {path.name} (blok={block_size})"
    plot_energy_map(energy_map, title, output_path)

    mean_energy = float(np.mean(energy_map))
    max_energy = float(np.max(energy_map))
    std_energy = float(np.std(energy_map))
    relative_std = (std_energy / mean_energy) if mean_energy > 0 else 0.0

    if mean_energy < FLAT_ENERGY_THRESHOLD:
        interpretation = "gözle görülür yüksek frekans enerjisi yok (düz/basit içerik veya sıkıştırma sonrası temiz alan)."
    elif relative_std < UNIFORM_RELATIVE_STD_THRESHOLD:
        interpretation = (
            "yüksek ortalama ve düşük standart sapma birlikte, tüm görsele yayılmış "
            "tekdüze gürültüyü işaret eder (LSB-steganografi ile tutarlı)."
        )
    else:
        interpretation = (
            "yüksek frekans enerjisi bloklar arasında belirgin değişkenlik gösteriyor; "
            "bu, tekdüze gürültüden çok içerik-bağımlı (kenar/detay) frekans dağılımıyla tutarlı."
        )

    summary = (
        f"{energy_map.shape[0]}x{energy_map.shape[1]} blok, ortalama yüksek frekans enerjisi "
        f"{mean_energy:.1f} (std={std_energy:.1f}, maks={max_energy:.1f}) — {interpretation}"
    )

    return {
        "file": str(path),
        "width": gray.shape[1],
        "height": gray.shape[0],
        "block_size": block_size,
        "block_rows": energy_map.shape[0],
        "block_cols": energy_map.shape[1],
        "mean_high_freq_energy": round(mean_energy, 2),
        "std_high_freq_energy": round(std_energy, 2),
        "max_high_freq_energy": round(max_energy, 2),
        "output": str(output_path),
        "analysis_summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Analiz edilecek görsel yolu")
    parser.add_argument(
        "--block-size", type=int, default=DEFAULT_BLOCK_SIZE,
        help=f"DCT blok boyutu (piksel), varsayılan {DEFAULT_BLOCK_SIZE}",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Isı haritası PNG çıktı yolu (varsayılan: docs/dct-<dosya-adi>.png)",
    )
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:                  {result['file']}")
    print(f"Boyutlar:               {result['width']}x{result['height']}")
    print(f"Blok boyutu:            {result['block_size']} ({result['block_rows']}x{result['block_cols']} blok)")
    print(f"Ort. yüksek frek. enrj: {result['mean_high_freq_energy']}")
    print(f"Std yüksek frek. enrj:  {result['std_high_freq_energy']}")
    print(f"Maks yüksek frek. enrj: {result['max_high_freq_energy']}")
    print(f"Isı haritası kaydedildi: {result['output']}")
    print(f"Özet:                   {result['analysis_summary']}")


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        print(f"Hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1
    if args.block_size <= 0:
        print("Hata: --block-size pozitif bir tam sayı olmalı", file=sys.stderr)
        return 1

    safe_name = args.file.name.replace(".", "_")
    output_path = args.output or Path("docs") / f"dct-{safe_name}.png"

    try:
        result = analyze(args.file, args.block_size, output_path)
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
