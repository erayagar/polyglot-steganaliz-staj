#!/usr/bin/env python3
"""Bir dosyayı sabit boyutlu bloklara bölüp her blok için Shannon entropy
hesaplar ve blok bazlı entropy değerlerini matplotlib ile grafikleştirir.

Polyglot dosyalarda görsel bölgesi ile arkasına eklenmiş video bölgesi
genellikle farklı entropy karakteristiğine sahiptir; bu script iki bölge
arasındaki geçişi grafikte görünür kılmayı amaçlar.

Kullanım:
    python scripts/entropy.py --file samples/polyglot_png.png
    python scripts/entropy.py --file samples/sample.jpg --block-size 512 --output docs/entropy-sample-jpg.png
"""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from detect_trailer import analyze as detect_trailer_analyze

DEFAULT_BLOCK_SIZE = 256


def shannon_entropy(block: bytes) -> float:
    """Bir bayt bloğunun Shannon entropy'sini (bit/bayt, 0-8 aralığında) hesaplar."""
    if not block:
        return 0.0
    counts = Counter(block)
    length = len(block)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def compute_block_entropies(data: bytes, block_size: int) -> list[dict]:
    blocks = []
    for offset in range(0, len(data), block_size):
        block = data[offset:offset + block_size]
        blocks.append({
            "offset": offset,
            "size": len(block),
            "entropy": shannon_entropy(block),
        })
    return blocks


def find_boundary_offset(path: Path):
    """detect_trailer ile görsel/video sınır offset'ini bulmayı dener.

    Dosya PNG/JPEG değilse veya trailer'da bilinen bir video imzası
    bulunamazsa None döner (sınır çizgisi grafikte gösterilmez).
    """
    try:
        result = detect_trailer_analyze(path)
    except (ValueError, FileNotFoundError):
        return None
    if result["polyglot_status"]:
        return result["hidden_video_offset"]
    return None


def plot_entropy(blocks: list[dict], block_size: int, boundary_offset, title: str, output_path: Path) -> None:
    offsets = [b["offset"] for b in blocks]
    entropies = [b["entropy"] for b in blocks]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(offsets, entropies, color="#1f77b4", linewidth=1)
    ax.set_xlabel(f"Dosya offset (bayt, blok boyutu={block_size})")
    ax.set_ylabel("Shannon entropy (bit/bayt, 0-8)")
    ax.set_ylim(0, 8.2)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    if boundary_offset is not None:
        ax.axvline(
            boundary_offset,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Görsel/video sınırı (offset {boundary_offset})",
        )
        ax.legend()

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Analiz edilecek dosya yolu")
    parser.add_argument(
        "--block-size", type=int, default=DEFAULT_BLOCK_SIZE,
        help=f"Blok boyutu (bayt), varsayılan {DEFAULT_BLOCK_SIZE}",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Grafik PNG çıktı yolu (varsayılan: docs/entropy-<dosya-adi>.png)",
    )
    parser.add_argument("--json", action="store_true", help="Blok entropy değerlerini JSON olarak yazdır")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        print(f"Hata: dosya bulunamadı: {args.file}", file=sys.stderr)
        return 1
    if args.block_size <= 0:
        print("Hata: --block-size pozitif bir tam sayı olmalı", file=sys.stderr)
        return 1

    data = args.file.read_bytes()
    blocks = compute_block_entropies(data, args.block_size)
    boundary_offset = find_boundary_offset(args.file)

    safe_name = args.file.name.replace(".", "_")
    output_path = args.output or Path("docs") / f"entropy-{safe_name}.png"
    title = f"Blok Bazlı Shannon Entropy — {args.file.name}"
    plot_entropy(blocks, args.block_size, boundary_offset, title, output_path)

    print(f"Dosya:               {args.file}")
    print(f"Dosya boyutu:        {len(data)} bayt")
    print(f"Blok sayısı:         {len(blocks)} (blok boyutu={args.block_size})")
    if boundary_offset is not None:
        print(f"Görsel/video sınırı: offset {boundary_offset} (0x{boundary_offset:X})")
    else:
        print("Görsel/video sınırı: tespit edilemedi (polyglot değil veya bilinmeyen imza)")
    print(f"Grafik kaydedildi:   {output_path}")

    if args.json:
        print(json.dumps(blocks, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
