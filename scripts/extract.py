#!/usr/bin/env python3
"""Bir polyglot (görsel+video) dosyasını, görselin gerçek EOF işaretine
(IEND/EOI) göre ikiye ayırıp gizli video akışını bağımsız bir .mp4 dosyası
olarak ayıklar (unpolyglot).

Kullanım:
    python scripts/extract.py --file samples/polyglot_png.png
    python scripts/extract.py --file samples/polyglot_jpg.jpg --output-dir samples/extracted --json
"""
import argparse
import json
import sys
from pathlib import Path

from detect_trailer import analyze as analyze_trailer

DEFAULT_OUTPUT_DIR = Path("samples/extracted")


def extract(path: Path, output_dir: Path, save_image: bool = False) -> dict:
    trailer_info = analyze_trailer(path)

    if not trailer_info["polyglot_status"]:
        raise ValueError(
            f"'{path}' bir polyglot dosya değil (gizli video imzası bulunamadı): "
            f"{trailer_info['analysis_summary']}"
        )

    data = path.read_bytes()
    split_offset = trailer_info["image_end_offset"]
    image_bytes = data[:split_offset]
    video_bytes = data[split_offset:]

    output_dir.mkdir(parents=True, exist_ok=True)

    stem = path.stem
    video_output_path = output_dir / f"{stem}_extracted.mp4"
    video_output_path.write_bytes(video_bytes)

    image_output_path = None
    if save_image:
        image_ext = ".png" if trailer_info["image_format"] == "png" else ".jpg"
        image_output_path = output_dir / f"{stem}_extracted_image{image_ext}"
        image_output_path.write_bytes(image_bytes)

    size_match = len(data) == len(image_bytes) + len(video_bytes)

    return {
        "file": str(path),
        "file_size": len(data),
        "image_format": trailer_info["image_format"],
        "split_offset": split_offset,
        "image_size": len(image_bytes),
        "video_size": len(video_bytes),
        "size_match": size_match,
        "extracted_video_path": str(video_output_path),
        "extracted_image_path": str(image_output_path) if image_output_path else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Ayıklanacak polyglot dosya yolu")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Ayıklanan dosyaların yazılacağı dizin (varsayılan: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--save-image", action="store_true",
        help="Ayıklanan görsel kısmını da ayrı bir dosya olarak kaydet (doğrulama amaçlı)",
    )
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:                 {result['file']}")
    print(f"Dosya boyutu:          {result['file_size']} bayt")
    print(f"Görsel formatı:        {result['image_format'].upper()}")
    print(f"Ayırma offset'i:       {result['split_offset']} (0x{result['split_offset']:X})")
    print(f"Görsel kısmı boyutu:   {result['image_size']} bayt")
    print(f"Video kısmı boyutu:    {result['video_size']} bayt")
    print(f"Boyut tutarlılığı:     {'OK' if result['size_match'] else 'UYUŞMUYOR'}")
    print(f"Ayıklanan video:       {result['extracted_video_path']}")
    if result["extracted_image_path"]:
        print(f"Ayıklanan görsel:      {result['extracted_image_path']}")


def main() -> int:
    args = parse_args()
    try:
        result = extract(args.file, args.output_dir, save_image=args.save_image)
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
