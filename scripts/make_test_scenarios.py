#!/usr/bin/env python3
"""Gün 10 test matrisi için türetilmiş örnek dosyaları üretir.

Mevcut samples/polyglot_png.png, samples/polyglot_jpg.jpg, samples/sample.png,
samples/sample.jpg, samples/sample.mp4 dosyalarından yola çıkarak iki farklı
"yeniden sıkıştırma/optimize etme" senaryosu ve bir ek temiz görsel üretir:

    recompressed_post_*  - Halihazırda video içeren bir polyglot dosya PIL ile
                            yeniden kaydedilir. PIL yalnızca dekode ettiği piksel
                            verisini yazdığından EOF sonrası trailer (gizli video)
                            bu işlemde kaybolur; bir platformun görseli sunucu
                            tarafında yeniden encode etmesini simüle eder.
    recompressed_pre_*   - Taşıyıcı görsel video eklenmeden önce farklı bir
                            sıkıştırma seviyesiyle yeniden kaydedilir, video bu
                            yeni taşıyıcının arkasına eklenir. Taşıyıcının iç
                            sıkıştırmasının trailer tespitini etkilemediğini
                            doğrulamak için kullanılır.
    clean_gradient.png   - Ek bir temiz (video içermeyen) referans görsel.

Kullanım:
    python scripts/make_test_scenarios.py
"""
from pathlib import Path

from PIL import Image

from make_polyglot import make_polyglot

SAMPLES_DIR = Path("samples")
OUTPUT_DIR = SAMPLES_DIR / "test_matrix"


def recompress_post_embedding(polyglot_path: Path, output_path: Path, **save_kwargs) -> None:
    with Image.open(polyglot_path) as img:
        img.load()
        img.save(output_path, **save_kwargs)


def recompress_pre_embedding(image_path: Path, video_path: Path, output_path: Path,
                              tmp_carrier: Path, **save_kwargs) -> None:
    with Image.open(image_path) as img:
        img.save(tmp_carrier, **save_kwargs)
    make_polyglot(tmp_carrier, video_path, output_path)
    tmp_carrier.unlink(missing_ok=True)


def make_clean_gradient(output_path: Path, size=(128, 128)) -> None:
    img = Image.new("RGB", size)
    pixels = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (x * 255 // size[0], y * 255 // size[1], 128)
    img.save(output_path)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    recompress_post_embedding(
        SAMPLES_DIR / "polyglot_png.png",
        OUTPUT_DIR / "recompressed_post_png.png",
        optimize=True,
    )
    recompress_post_embedding(
        SAMPLES_DIR / "polyglot_jpg.jpg",
        OUTPUT_DIR / "recompressed_post_jpg.jpg",
        quality=75, optimize=True,
    )

    recompress_pre_embedding(
        SAMPLES_DIR / "sample.png",
        SAMPLES_DIR / "sample.mp4",
        OUTPUT_DIR / "recompressed_pre_png.png",
        OUTPUT_DIR / "_tmp_carrier.png",
        optimize=True, compress_level=9,
    )
    recompress_pre_embedding(
        SAMPLES_DIR / "sample.jpg",
        SAMPLES_DIR / "sample.mp4",
        OUTPUT_DIR / "recompressed_pre_jpg.jpg",
        OUTPUT_DIR / "_tmp_carrier.jpg",
        quality=50,
    )

    make_clean_gradient(OUTPUT_DIR / "clean_gradient.png")

    print(f"Test senaryosu dosyaları üretildi: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.glob("*")):
        print(f"  {f.name}: {f.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
