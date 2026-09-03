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


# --- Gün 14: threat_score ve analysis_summary --------------------------
#
# Üç sinyal ağırlıklı olarak birleştirilir. Trailer tespiti (Gün 4) en güçlü
# ve en az yanlış-pozitif üreten sinyal olduğundan en yüksek ağırlığı alır;
# entropy farkı (Gün 5) ve boyut sapması (Gün 6) tamamlayıcı/destekleyici
# sinyaller oldukları için (bkz. Gün 6/7 raporlarındaki "tek başına kesin
# kanıt değil" notu) daha düşük ağırlıklarla katkıda bulunur.
TRAILER_WEIGHT = 60
ENTROPY_WEIGHT = 25
SIZE_WEIGHT = 15

# Bu değere ulaşan/geçen sinyal, o sinyalin ağırlığının tamamını alır
# (üstü kırpılır); aradaki değerler doğrusal olarak ölçeklenir.
ENTROPY_DELTA_FULL_SCORE_AT = 3.0  # bit/bayt
SIZE_DEVIATION_FULL_SCORE_AT = 100.0  # yüzde


def compute_threat_score(result: dict) -> int:
    """Trailer + entropy + boyut sapması sinyallerini 0-100 aralığında tek
    bir tehdit skoruna ağırlıklı olarak birleştirir."""
    score = 0.0

    if result["polyglot_status"]:
        score += TRAILER_WEIGHT

    entropy_delta = result["entropy"]["entropy_delta"]
    if entropy_delta:
        score += min(entropy_delta / ENTROPY_DELTA_FULL_SCORE_AT, 1.0) * ENTROPY_WEIGHT

    deviation_percent = result["size"]["deviation_percent"]
    if deviation_percent and deviation_percent > 0:
        score += min(deviation_percent / SIZE_DEVIATION_FULL_SCORE_AT, 1.0) * SIZE_WEIGHT

    return max(0, min(100, round(score)))


def build_analysis_summary(result: dict, threat_score: int) -> str:
    """Tespit edilen video boyutu/codec bilgisini de içeren, insan
    tarafından okunabilir bir özet metni üretir."""
    if not result["polyglot_status"]:
        return f"{result['trailer']['analysis_summary']} (threat_score={threat_score})"

    trailer = result["trailer"]
    summary = (
        f"Görsele gizlenmiş video tespit edildi: '{trailer['detected_signature']}' "
        f"imzası offset {trailer['hidden_video_offset']} konumunda bulundu "
        f"(threat_score={threat_score})."
    )

    video_meta = result["video_metadata"]
    if video_meta:
        summary += (
            f" Ayıklanan video: {video_meta['width']}x{video_meta['height']}, "
            f"{video_meta['duration_seconds']} sn, codec={video_meta['codec']}."
        )

    return summary
