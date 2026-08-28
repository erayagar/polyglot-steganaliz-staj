#!/usr/bin/env python3
"""detect_trailer, size_analysis ve entropy modüllerini tek bir pipeline'da
birleştirip bir görsel dosya için birleşik bir analiz raporu üretir.

Bu script herhangi bir tekil sinyali "kesin karar" olarak kullanmaz; her
modülün sonucunu yan yana raporlar. Sinyallerin ağırlıklı bir tehdit
skoruna dönüştürülmesi Gün 14'te (API katmanı) ele alınacaktır.

Kullanım:
    python scripts/analyze.py --file samples/polyglot_png.png
    python scripts/analyze.py --file samples/sample.jpg --json
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

from detect_trailer import analyze as detect_trailer_analyze
from entropy import DEFAULT_BLOCK_SIZE, compute_block_entropies
from size_analysis import analyze as size_analyze


def entropy_summary(data: bytes, block_size: int, boundary_offset) -> dict:
    blocks = compute_block_entropies(data, block_size)
    entropies = [b["entropy"] for b in blocks]
    result = {
        "block_size": block_size,
        "block_count": len(blocks),
        "mean_entropy": round(statistics.fmean(entropies), 3) if entropies else 0.0,
        "boundary_offset": boundary_offset,
        "mean_entropy_before_boundary": None,
        "mean_entropy_after_boundary": None,
        "entropy_delta": None,
    }
    if boundary_offset is not None:
        before = [b["entropy"] for b in blocks if b["offset"] < boundary_offset]
        after = [b["entropy"] for b in blocks if b["offset"] >= boundary_offset]
        if before and after:
            mean_before = statistics.fmean(before)
            mean_after = statistics.fmean(after)
            result["mean_entropy_before_boundary"] = round(mean_before, 3)
            result["mean_entropy_after_boundary"] = round(mean_after, 3)
            result["entropy_delta"] = round(abs(mean_after - mean_before), 3)
    return result


def analyze(path: Path, block_size: int = DEFAULT_BLOCK_SIZE) -> dict:
    data = path.read_bytes()
    trailer_result = detect_trailer_analyze(path)
    size_result = size_analyze(path)
    ent_result = entropy_summary(data, block_size, trailer_result["hidden_video_offset"])

    return {
        "file": str(path),
        "file_size": len(data),
        "polyglot_status": trailer_result["polyglot_status"],
        "trailer": trailer_result,
        "size": size_result,
        "entropy": ent_result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Analiz edilecek PNG/JPEG dosya yolu")
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE, help="Entropy blok boyutu (bayt)")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    trailer = result["trailer"]
    size = result["size"]
    ent = result["entropy"]

    print(f"Dosya:                 {result['file']}")
    print(f"Dosya boyutu:          {result['file_size']} bayt")
    print(f"[trailer] polyglot mu: {'EVET' if trailer['polyglot_status'] else 'hayır'}"
          + (f" (imza: {trailer['detected_signature']}, offset {trailer['hidden_video_offset']})"
             if trailer["polyglot_status"] else ""))
    print(f"[size]    şüpheli mi:  {'EVET' if size['suspicious'] else 'hayır'} (sapma %{size['deviation_percent']})")
    if ent["entropy_delta"] is not None:
        print(f"[entropy] sınır offset {ent['boundary_offset']}: "
              f"öncesi={ent['mean_entropy_before_boundary']} sonrası={ent['mean_entropy_after_boundary']} "
              f"(delta={ent['entropy_delta']})")
    else:
        print(f"[entropy] ortalama entropy: {ent['mean_entropy']} (görsel/video sınırı tespit edilemedi)")


def main() -> int:
    args = parse_args()
    try:
        result = analyze(args.file, block_size=args.block_size)
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
