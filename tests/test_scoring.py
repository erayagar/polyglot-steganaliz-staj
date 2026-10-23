import pytest

import analyze
from app import pipeline
from conftest import SAMPLES


def _score(path):
    return pipeline.compute_threat_score(analyze.analyze(path))


@pytest.mark.parametrize("name", ["sample.png", "sample.jpg", "lsb_stego_sample.png"])
def test_files_without_trailer_score_zero(name):
    assert _score(SAMPLES / name) == 0


@pytest.mark.parametrize("name", ["polyglot_png.png", "polyglot_jpg.jpg"])
def test_polyglots_score_high(name):
    assert _score(SAMPLES / name) >= 60


def test_unknown_trailer_scores_medium(tmp_path, sample_png):
    path = tmp_path / "zip.png"
    path.write_bytes(sample_png + b"PK\x03\x04" + bytes(range(256)) * 4)
    score = _score(path)
    assert pipeline.TRAILER_UNKNOWN_WEIGHT <= score < pipeline.TRAILER_WEIGHT + pipeline.TRAILER_UNKNOWN_WEIGHT


def test_entropy_is_measured_for_non_video_trailer(tmp_path, sample_png):
    path = tmp_path / "zip.png"
    path.write_bytes(sample_png + bytes(range(256)) * 4)
    result = analyze.analyze(path)
    assert result["entropy"]["entropy_delta"] is not None
