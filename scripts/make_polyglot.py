#!/usr/bin/env python3
"""Bir görselin arkasına bir MP4 videosunu ekleyerek sentetik bir polyglot dosya üretir.

Kullanım:
    python scripts/make_polyglot.py --image samples/sample.png --video samples/sample.mp4 --output samples/polyglot.png
"""
import argparse
import sys
from pathlib import Path

PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")
JPEG_SOI = bytes.fromhex("ffd8")
MP4_FTYP = b"ftyp"


def detect_image_format(data: bytes) -> str:
    if data.startswith(PNG_SIGNATURE):
        return "png"
    if data.startswith(JPEG_SOI):
        return "jpeg"
    raise ValueError("Görsel PNG veya JPEG imzasıyla başlamıyor (desteklenmeyen format)")


def validate_mp4(data: bytes) -> None:
    if data[4:8] != MP4_FTYP:
        raise ValueError("Video dosyasının 4-8. baytlarında 'ftyp' imzası bulunamadı (MP4 değil)")


def make_polyglot(image_path: Path, video_path: Path, output_path: Path) -> None:
    image_bytes = image_path.read_bytes()
    video_bytes = video_path.read_bytes()

    image_format = detect_image_format(image_bytes)
    validate_mp4(video_bytes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes + video_bytes)

    print(f"Görsel formatı: {image_format.upper()}")
    print(f"Görsel boyutu:  {len(image_bytes)} bayt")
    print(f"Video boyutu:   {len(video_bytes)} bayt")
    print(f"Çıktı boyutu:   {output_path.stat().st_size} bayt")
    print(f"Gizli video başlangıç offset'i: {len(image_bytes)} (0x{len(image_bytes):X})")
    print(f"Yazıldı: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path, help="Kaynak PNG/JPEG görsel yolu")
    parser.add_argument("--video", required=True, type=Path, help="Kaynak MP4 video yolu")
    parser.add_argument("--output", required=True, type=Path, help="Üretilecek polyglot dosya yolu")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        make_polyglot(args.image, args.video, args.output)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
