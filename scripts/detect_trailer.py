#!/usr/bin/env python3
"""Bir PNG/JPEG dosyasının gerçek EOF işaretinden (IEND/EOI) sonra kalan
trailer baytlarını tarayıp, bilinen video/konteyner imzalarını arar.

Kullanım:
    python scripts/detect_trailer.py --file samples/polyglot_png.png
    python scripts/detect_trailer.py --file samples/sample.png --json
"""
import argparse
import json
import sys
from pathlib import Path

from make_polyglot import JPEG_SOI, PNG_SIGNATURE, detect_image_format

# JPEG marker'ları arasında uzunluk alanı olmayanlar: TEM (0x01) ve
# restart marker'ları (RST0-RST7, 0xD0-0xD7). SOI/EOI ayrıca ele alınır.
NO_LENGTH_MARKERS = {0x01} | set(range(0xD0, 0xD8))

MIN_TRAILER_SIZE = 16

# (imza adı, aranacak baytlar, imzanın box/dosya başlangıcının kaç bayt
# gerisinde olduğu) — ftyp/moov/mdat bir ISO-BMFF box'ının type alanıdır
# ve type'tan önce 4 baytlık size alanı gelir; RIFF ve EBML(WebM/MKV)
# imzaları doğrudan dosyanın ilk baytlarıdır.
VIDEO_SIGNATURES = [
    ("mp4/ftyp", b"ftyp", 4),
    ("mp4/moov", b"moov", 4),
    ("mp4/mdat", b"mdat", 4),
    ("avi/riff", b"RIFF", 0),
    ("webm-mkv/ebml", b"\x1a\x45\xdf\xa3", 0),
]


def find_png_end(data: bytes) -> int:
    offset = len(PNG_SIGNATURE)
    n = len(data)
    while offset + 8 <= n:
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 8 + length + 4
        if chunk_type == b"IEND":
            return chunk_end
        if chunk_end <= offset:
            raise ValueError(f"PNG chunk'ı ilerlemiyor (offset {offset}), dosya bozuk olabilir")
        offset = chunk_end
    raise ValueError("PNG dosyasında IEND chunk'ı bulunamadı (bozuk dosya)")


def find_jpeg_end(data: bytes) -> int:
    offset = len(JPEG_SOI)
    n = len(data)
    while offset < n:
        if data[offset] != 0xFF:
            raise ValueError(f"JPEG marker beklenirken 0x{data[offset]:02X} bulundu (offset {offset}), dosya bozuk olabilir")
        marker = data[offset + 1]
        offset += 2

        if marker == 0xD9:  # EOI
            return offset

        if marker in NO_LENGTH_MARKERS:
            continue

        length = int.from_bytes(data[offset:offset + 2], "big")
        offset += length

        if marker == 0xDA:  # SOS: uzunluk alanından sonra entropy-coded veri gelir
            while offset < n:
                if data[offset] == 0xFF:
                    nxt = data[offset + 1] if offset + 1 < n else 0x00
                    if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                        offset += 2  # stuffed bayt veya restart marker, veri devam ediyor
                        continue
                    break  # gerçek bir marker'a ulaşıldı
                offset += 1

    raise ValueError("JPEG dosyasında EOI (FF D9) bulunamadı (bozuk dosya)")


def find_image_end(data: bytes, image_format: str) -> int:
    if image_format == "png":
        return find_png_end(data)
    return find_jpeg_end(data)


def scan_video_signature(trailer: bytes):
    if len(trailer) < MIN_TRAILER_SIZE:
        return None
    for name, sig, back_offset in VIDEO_SIGNATURES:
        pos = trailer.find(sig)
        if pos == -1:
            continue
        box_start = pos - back_offset
        if box_start < 0:
            continue
        return {"signature": name, "trailer_offset": box_start}
    return None


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    file_size = len(data)

    image_format = detect_image_format(data)
    image_end = find_image_end(data, image_format)
    trailer = data[image_end:]
    trailer_size = len(trailer)

    match = scan_video_signature(trailer)

    if match is not None:
        hidden_offset = image_end + match["trailer_offset"]
        summary = (
            f"EOF sonrası {trailer_size} bayt trailer bulundu; "
            f"'{match['signature']}' imzası offset {hidden_offset} "
            f"(0x{hidden_offset:X}) konumunda tespit edildi — muhtemel gizli video/medya."
        )
        return {
            "file": str(path),
            "file_size": file_size,
            "image_format": image_format,
            "image_end_offset": image_end,
            "trailer_size": trailer_size,
            "polyglot_status": True,
            "detected_signature": match["signature"],
            "hidden_video_offset": hidden_offset,
            "analysis_summary": summary,
        }

    if trailer_size > 0:
        summary = (
            f"EOF sonrası {trailer_size} bayt fazladan veri var ancak bilinen bir "
            f"video/konteyner imzası bulunamadı (muhtemelen zararsız padding/metadata)."
        )
    else:
        summary = "EOF sonrası fazladan veri yok, dosya temiz."

    return {
        "file": str(path),
        "file_size": file_size,
        "image_format": image_format,
        "image_end_offset": image_end,
        "trailer_size": trailer_size,
        "polyglot_status": False,
        "detected_signature": None,
        "hidden_video_offset": None,
        "analysis_summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Taranacak PNG/JPEG dosya yolu")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:                {result['file']}")
    print(f"Dosya boyutu:         {result['file_size']} bayt")
    print(f"Görsel formatı:       {result['image_format'].upper()}")
    print(f"Görsel bitiş offset'i: {result['image_end_offset']} (0x{result['image_end_offset']:X})")
    print(f"Trailer boyutu:       {result['trailer_size']} bayt")
    print(f"Polyglot mu?          {'EVET' if result['polyglot_status'] else 'hayır'}")
    if result["detected_signature"]:
        print(f"Tespit edilen imza:   {result['detected_signature']}")
        print(f"Gizli video offset'i: {result['hidden_video_offset']} (0x{result['hidden_video_offset']:X})")
    print(f"Özet:                 {result['analysis_summary']}")


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
