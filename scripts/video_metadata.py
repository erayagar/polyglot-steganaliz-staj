#!/usr/bin/env python3
"""Ayıklanmış (veya herhangi bir) bir video dosyasının meta verisini
(kare sayısı, süre, çözünürlük, codec) çıkarır.

Birincil yöntem `ffprobe -print_format json`; ffprobe bulunamazsa veya
başarısız olursa OpenCV `cv2.VideoCapture` ile yedek (fallback) okuma
yapılır. İki yöntem de kullanılabiliyorsa ikisinin sonucu karşılaştırılıp
tek bir yapılandırılmış sonuçta birleştirilir.

Kullanım:
    python scripts/video_metadata.py --file samples/extracted/polyglot_png_extracted.mp4
    python scripts/video_metadata.py --file samples/extracted/polyglot_jpg_extracted.mp4 --json
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _probe_ffprobe(path: Path) -> Optional[dict]:
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin is None:
        return None

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None

    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if video_stream is None:
        return None

    fmt = data.get("format", {})

    duration_raw = video_stream.get("duration") or fmt.get("duration")
    duration = float(duration_raw) if duration_raw is not None else None

    nb_frames_raw = video_stream.get("nb_frames")
    frame_count = int(nb_frames_raw) if nb_frames_raw and nb_frames_raw.isdigit() else None

    fps = None
    r_frame_rate = video_stream.get("r_frame_rate")
    if r_frame_rate and "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        den = float(den)
        if den:
            fps = round(float(num) / den, 3)

    if frame_count is None and fps and duration:
        frame_count = round(fps * duration)

    return {
        "source": "ffprobe",
        "frame_count": frame_count,
        "duration_seconds": round(duration, 3) if duration is not None else None,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": fps,
        "codec": video_stream.get("codec_name"),
        "container_format": fmt.get("format_name"),
    }


def _probe_opencv(path: Path) -> Optional[dict]:
    try:
        import cv2
    except ImportError:
        return None

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        return None

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or None
    fps = cap.get(cv2.CAP_PROP_FPS) or None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = (
        "".join(chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00")
        if fourcc_int
        else None
    )
    cap.release()

    duration = round(frame_count / fps, 3) if frame_count and fps else None

    return {
        "source": "opencv",
        "frame_count": frame_count,
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "fps": round(fps, 3) if fps else None,
        "codec": codec,
        "container_format": None,
    }


def get_metadata(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    ffprobe_result = _probe_ffprobe(path)
    opencv_result = _probe_opencv(path)

    if ffprobe_result is None and opencv_result is None:
        raise ValueError(f"'{path}' ne ffprobe ne de OpenCV ile bir video olarak okunabildi.")

    primary = ffprobe_result or opencv_result
    used_fallback = ffprobe_result is None

    return {
        "file": str(path),
        "file_size": path.stat().st_size,
        "frame_count": primary["frame_count"],
        "duration_seconds": primary["duration_seconds"],
        "width": primary["width"],
        "height": primary["height"],
        "fps": primary["fps"],
        "codec": primary["codec"],
        "container_format": primary["container_format"],
        "primary_source": primary["source"],
        "used_opencv_fallback": used_fallback,
        "ffprobe_result": ffprobe_result,
        "opencv_result": opencv_result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Meta verisi çıkarılacak video dosyası")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdır")
    return parser.parse_args()


def print_report(result: dict) -> None:
    print(f"Dosya:                 {result['file']}")
    print(f"Dosya boyutu:          {result['file_size']} bayt")
    print(f"Kare sayısı:           {result['frame_count']}")
    print(f"Süre:                  {result['duration_seconds']} sn")
    print(f"Çözünürlük:            {result['width']}x{result['height']}")
    print(f"FPS:                   {result['fps']}")
    print(f"Codec:                 {result['codec']}")
    print(f"Konteyner formatı:     {result['container_format']}")
    print(f"Birincil kaynak:       {result['primary_source']}"
          + (" (OpenCV yedek)" if result["used_opencv_fallback"] else " (ffprobe)"))


def main() -> int:
    args = parse_args()
    try:
        result = get_metadata(args.file)
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
