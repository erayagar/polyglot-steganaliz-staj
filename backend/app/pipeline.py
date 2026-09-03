"""1-2. hafta script'lerini (`scripts/`) API katmanına bağlayan pipeline.

`scripts/` bir paket değil; modülleri birbirini düz (bare) isimle import
ediyor (örn. `from detect_trailer import analyze`). Bu yapıyı bozmamak için
`scripts/` dizini burada `sys.path`'e eklenip modüller olduğu gibi import
edilir — script'leri paketleştirmek/taşımak bu günün kapsamı dışında
tutuldu (bkz. PLAN.md Gün 13 notu: "gerekirse").

`run_pipeline` CPU-yoğun (dosya okuma + entropy hesabı + olası extraction)
tamamen senkron bir fonksiyondur; event loop'u bloklamaması bu fonksiyonun
kendi sorumluluğu değil, çağıran tarafın (`asyncio.to_thread` ile
`backend/app/main.py`) sorumluluğudur.
"""
import statistics
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import detect_trailer  # noqa: E402
import entropy as entropy_module  # noqa: E402
import extract as extract_module  # noqa: E402
import size_analysis  # noqa: E402
import video_metadata  # noqa: E402

MEDIA_DIR = Path(__file__).resolve().parent / "media"


def _entropy_summary(data: bytes, boundary_offset: int | None) -> dict:
    blocks = entropy_module.compute_block_entropies(data, entropy_module.DEFAULT_BLOCK_SIZE)
    entropies = [b["entropy"] for b in blocks]
    result = {
        "mean_entropy": round(statistics.fmean(entropies), 3) if entropies else 0.0,
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


def run_pipeline(saved_path: Path) -> dict:
    """Gün 4/6/8/9'daki trailer, size, entropy, extraction ve video meta
    verisi adımlarını tek bir sonuç sözlüğünde birleştirir.

    Dosya polyglot değilse extraction/video-metadata adımları atlanır
    (extract.extract zaten polyglot olmayan dosyalarda ValueError fırlatır).
    """
    data = saved_path.read_bytes()
    trailer_result = detect_trailer.analyze(saved_path)
    size_result = size_analysis.analyze(saved_path)
    ent_result = _entropy_summary(data, trailer_result["hidden_video_offset"])

    extracted_video_url = None
    video_metadata_result = None

    if trailer_result["polyglot_status"]:
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        extraction = extract_module.extract(saved_path, MEDIA_DIR)
        video_path = Path(extraction["extracted_video_path"])
        extracted_video_url = f"/media/{video_path.name}"
        try:
            video_metadata_result = video_metadata.get_metadata(video_path)
        except (ValueError, FileNotFoundError):
            video_metadata_result = None

    return {
        "file": str(saved_path),
        "file_size": len(data),
        "polyglot_status": trailer_result["polyglot_status"],
        "trailer": trailer_result,
        "size": size_result,
        "entropy": ent_result,
        "extracted_video_url": extracted_video_url,
        "video_metadata": video_metadata_result,
    }
