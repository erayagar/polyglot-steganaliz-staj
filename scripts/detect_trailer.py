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

# Video olmayan ama görselin arkasına sık eklenen dosya türleri. Bunlar
# polyglot_status'u (gizli video) etkilemez; yalnızca "EOF sonrası veri ne
# olabilir" sorusuna yanıt olarak raporlanır.
OTHER_SIGNATURES = [
    ("zip", b"PK\x03\x04"),
    ("rar", b"Rar!\x1a\x07"),
    ("7z", b"7z\xbc\xaf\x27\x1c"),
    ("pdf", b"%PDF-"),
]


def read_jpeg_marker(data: bytes, offset: int) -> tuple[int, int]:
    """`offset`'teki JPEG marker'ını okuyup `(marker, marker_sonrası_offset)`
    döndürür. Standardın izin verdiği art arda 0xFF dolgu (fill) baytlarını
    atlar; dosya marker ortasında biterse `ValueError`."""
    n = len(data)
    if data[offset] != 0xFF:
        raise ValueError(f"JPEG marker beklenirken 0x{data[offset]:02X} bulundu (offset {offset}), dosya bozuk olabilir")
    offset += 1
    while offset < n and data[offset] == 0xFF:
        offset += 1
    if offset >= n:
        raise ValueError("JPEG dosyası bir marker'ın ortasında bitiyor (bozuk dosya)")
    return data[offset], offset + 1


def read_jpeg_segment_length(data: bytes, offset: int) -> int:
    """`offset`'teki 2 baytlık segment uzunluk alanını okur; alan eksikse
    veya geçersizse (< 2, uzunluk alanı kendini de kapsar) `ValueError`."""
    if offset + 2 > len(data):
        raise ValueError(f"JPEG segment uzunluk alanı eksik (offset {offset}), dosya bozuk olabilir")
    length = int.from_bytes(data[offset:offset + 2], "big")
    if length < 2:
        raise ValueError(f"Geçersiz JPEG segment uzunluğu {length} (offset {offset}), dosya bozuk olabilir")
    return length


def find_png_end(data: bytes) -> int:
    """PNG chunk zincirini `IEND` chunk'ına kadar yürüyüp, chunk'ın (CRC
    dahil) bittiği bayt offset'ini döndürür — görselin gerçek EOF'u."""
    offset = len(PNG_SIGNATURE)
    n = len(data)
    while offset + 8 <= n:
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 8 + length + 4
        if chunk_end > n:
            raise ValueError(f"PNG chunk'ı ({chunk_type!r}, offset {offset}) dosya sonunu aşıyor (bozuk dosya)")
        if chunk_type == b"IEND":
            return chunk_end
        offset = chunk_end
    raise ValueError("PNG dosyasında IEND chunk'ı bulunamadı (bozuk dosya)")


def find_jpeg_end(data: bytes) -> int:
    """JPEG marker zincirini `EOI` (FFD9) marker'ına kadar yürüyüp, onun
    bittiği bayt offset'ini döndürür — görselin gerçek EOF'u."""
    offset = len(JPEG_SOI)
    n = len(data)
    while offset < n:
        marker, offset = read_jpeg_marker(data, offset)

        if marker == 0xD9:  # EOI
            return offset

        if marker in NO_LENGTH_MARKERS:
            continue

        offset += read_jpeg_segment_length(data, offset)

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
    """Format'a göre `find_png_end`/`find_jpeg_end`'e yönlendiren ortak
    giriş noktası."""
    if image_format == "png":
        return find_png_end(data)
    return find_jpeg_end(data)


def _is_box_type(raw: bytes) -> bool:
    """ISO-BMFF box type'ı 4 yazdırılabilir ASCII karakterden oluşur."""
    return len(raw) == 4 and all(0x20 <= b <= 0x7E for b in raw)


def _valid_iso_bmff(trailer: bytes, start: int) -> bool:
    """`start`'tan itibaren en az iki geçerli ISO-BMFF box'ı (veya trailer
    sonuna kadar uzanan tek bir box) yürünebiliyor mu? Düz metin içinde
    geçen "moov"/"mdat" kelimeleri bu kontrolü geçemez."""
    n = len(trailer)
    offset = start
    boxes = 0
    while offset + 8 <= n and boxes < 2:
        size = int.from_bytes(trailer[offset:offset + 4], "big")
        box_type = trailer[offset + 4:offset + 8]
        if not _is_box_type(box_type):
            return False
        if boxes == 0 and box_type == b"ftyp" and not _is_box_type(trailer[offset + 8:offset + 12]):
            return False  # ftyp'ten sonra 4 karakterlik major brand gelmeli
        if size == 0:  # box dosya sonuna kadar uzanıyor
            return True
        if size == 1:  # 64-bit "largesize" alanı
            if offset + 16 > n:
                return False
            size = int.from_bytes(trailer[offset + 8:offset + 16], "big")
            if size < 16:
                return False
        elif size < 8:
            return False
        if offset + size > n:
            return False
        offset += size
        boxes += 1
        if offset == n:
            return True
    return boxes >= 2


def _valid_riff(trailer: bytes, start: int) -> bool:
    """`RIFF<size>AVI ` biçiminde bir AVI konteyneri mi?"""
    size = int.from_bytes(trailer[start + 4:start + 8], "little")
    return trailer[start + 8:start + 12] == b"AVI " and size >= 4


def _valid_ebml(trailer: bytes, start: int) -> bool:
    """EBML header'ının (uzunluğu ilk VINT ile kodlanır) DocType olarak
    `webm` veya `matroska` içerip içermediğine bakar."""
    first = trailer[start + 4:start + 5]
    if not first or first[0] == 0:
        return False
    vint_len = 8 - first[0].bit_length() + 1
    header = trailer[start + 4 + vint_len:start + 4 + vint_len + 64]
    return b"webm" in header or b"matroska" in header


SIGNATURE_VALIDATORS = {
    "mp4/ftyp": _valid_iso_bmff,
    "mp4/moov": _valid_iso_bmff,
    "mp4/mdat": _valid_iso_bmff,
    "avi/riff": _valid_riff,
    "webm-mkv/ebml": _valid_ebml,
}


def scan_video_signature(trailer: bytes):
    """Trailer baytları içinde `VIDEO_SIGNATURES`'ı arar ve her adayı
    konteyner yapısına göre doğrular (bkz. `SIGNATURE_VALIDATORS`); en
    küçük offset'teki geçerli eşleşmeyi seçer. En küçük trailer eşiğinin
    (`MIN_TRAILER_SIZE`) altındaki veriyi (zararsız padding/metadata
    olabileceğinden) hiç taramaz. Eşleşme bulunursa `{"signature",
    "trailer_offset"}` döner, aksi halde `None`."""
    if len(trailer) < MIN_TRAILER_SIZE:
        return None
    best = None
    for name, sig, back_offset in VIDEO_SIGNATURES:
        validate = SIGNATURE_VALIDATORS[name]
        pos = trailer.find(sig)
        while pos != -1:
            box_start = pos - back_offset
            if best is not None and box_start >= best["trailer_offset"]:
                break
            if box_start >= 0 and validate(trailer, box_start):
                best = {"signature": name, "trailer_offset": box_start}
                break
            pos = trailer.find(sig, pos + 1)
    return best


def scan_other_signature(trailer: bytes):
    """Video imzası bulunamayan trailer'da bilinen diğer dosya türlerini
    (`OTHER_SIGNATURES`) arar; en küçük offset'tekinin adını döner."""
    if len(trailer) < MIN_TRAILER_SIZE:
        return None
    hits = [(trailer.find(sig), name) for name, sig in OTHER_SIGNATURES]
    hits = [h for h in hits if h[0] != -1]
    return min(hits)[1] if hits else None


def analyze_bytes(data: bytes, label: str) -> dict:
    """`analyze` ile aynı sonucu, dosyayı yeniden okumadan bellekteki
    baytlar üzerinde üretir (`pipeline.py` dosyayı yalnızca bir kez okur)."""
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
            "file": label,
            "file_size": file_size,
            "image_format": image_format,
            "image_end_offset": image_end,
            "trailer_size": trailer_size,
            "polyglot_status": True,
            "detected_signature": match["signature"],
            "hidden_video_offset": hidden_offset,
            "other_signature": None,
            "analysis_summary": summary,
        }

    other = scan_other_signature(trailer)
    if other is not None:
        summary = (
            f"EOF sonrası {trailer_size} bayt fazladan veri var; video imzası yok ancak "
            f"'{other}' dosya imzası bulundu — görsele gizlenmiş veri olabilir, şüpheli."
        )
    elif trailer_size >= MIN_TRAILER_SIZE:
        summary = (
            f"EOF sonrası {trailer_size} bayt fazladan veri var; bilinen bir video/konteyner "
            f"imzası bulunamadı ancak bu boyutta veri gizli içerik taşıyor olabilir, şüpheli."
        )
    elif trailer_size > 0:
        summary = (
            f"EOF sonrası {trailer_size} bayt fazladan veri var (eşik {MIN_TRAILER_SIZE} baytın "
            f"altında, muhtemelen zararsız padding)."
        )
    else:
        summary = "EOF sonrası fazladan veri yok, dosya temiz."

    return {
        "file": label,
        "file_size": file_size,
        "image_format": image_format,
        "image_end_offset": image_end,
        "trailer_size": trailer_size,
        "polyglot_status": False,
        "detected_signature": None,
        "hidden_video_offset": None,
        "other_signature": other,
        "analysis_summary": summary,
    }


def analyze(path: Path) -> dict:
    """Dosyanın EOF sonrası trailer'ını tarayıp polyglot durumunu,
    tespit edilen imzayı ve gizli video offset'ini raporlar. `extract.py`
    ve CLI bu fonksiyonu modülün ana giriş noktası olarak kullanır."""
    return analyze_bytes(path.read_bytes(), str(path))


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
    if result["other_signature"]:
        print(f"Diğer dosya imzası:   {result['other_signature']}")
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
