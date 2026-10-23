"""Testlerin `scripts/` modüllerini ve `backend/app` paketini, uygulamanın
kendisiyle aynı şekilde (düz isimle) import edebilmesi için yol ayarı."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for sub in ("scripts", "backend"):
    path = str(ROOT / sub)
    if path not in sys.path:
        sys.path.insert(0, path)

SAMPLES = ROOT / "samples"


@pytest.fixture
def sample_png() -> bytes:
    return (SAMPLES / "sample.png").read_bytes()


@pytest.fixture
def sample_jpg() -> bytes:
    return (SAMPLES / "sample.jpg").read_bytes()


@pytest.fixture
def sample_mp4() -> bytes:
    return (SAMPLES / "sample.mp4").read_bytes()
