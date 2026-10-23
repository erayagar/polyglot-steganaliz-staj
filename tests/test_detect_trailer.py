import pytest

import detect_trailer
import extract


def test_jpeg_ending_with_lone_ff_raises_value_error():
    with pytest.raises(ValueError):
        detect_trailer.find_jpeg_end(b"\xff\xd8\xff")


def test_jpeg_fill_bytes_before_marker_are_skipped():
    assert detect_trailer.find_jpeg_end(b"\xff\xd8\xff\xff\xd9") == 5


def test_jpeg_invalid_segment_length_raises_value_error():
    with pytest.raises(ValueError):
        detect_trailer.find_jpeg_end(b"\xff\xd8\xff\xe0\x00\x01")


def test_png_chunk_past_eof_raises_value_error(sample_png):
    with pytest.raises(ValueError):
        detect_trailer.find_png_end(sample_png[:40])


def test_plain_text_mentioning_signatures_is_not_a_video():
    trailer = b"This is a comment mentioning RIFF and moov words."
    assert detect_trailer.scan_video_signature(trailer) is None


@pytest.mark.parametrize("fixture", ["sample_png", "sample_jpg"])
def test_clean_samples_are_not_polyglot(fixture, request):
    result = detect_trailer.analyze_bytes(request.getfixturevalue(fixture), "x")
    assert result["polyglot_status"] is False
    assert result["trailer_size"] == 0


@pytest.mark.parametrize("fixture", ["sample_png", "sample_jpg"])
def test_appended_mp4_is_detected_at_image_end(fixture, request, sample_mp4):
    image = request.getfixturevalue(fixture)
    result = detect_trailer.analyze_bytes(image + sample_mp4, "x")
    assert result["polyglot_status"] is True
    assert result["detected_signature"] == "mp4/ftyp"
    assert result["hidden_video_offset"] == len(image)


def test_junk_prefix_before_video_is_skipped_on_extraction(tmp_path, sample_png, sample_mp4):
    junk = b"JUNK" * 10
    polyglot = tmp_path / "p.png"
    polyglot.write_bytes(sample_png + junk + sample_mp4)

    info = detect_trailer.analyze(polyglot)
    assert info["image_end_offset"] == len(sample_png)
    assert info["hidden_video_offset"] == len(sample_png) + len(junk)

    result = extract.extract(polyglot, tmp_path / "out")
    assert result["prefix_size"] == len(junk)
    assert result["size_match"] is True
    video_path = tmp_path / "out" / "p_extracted.mp4"
    assert result["extracted_video_path"] == str(video_path)
    assert video_path.read_bytes() == sample_mp4


def test_avi_and_webm_are_detected_with_matching_extension(tmp_path, sample_png):
    avi = b"RIFF" + (100).to_bytes(4, "little") + b"AVI LIST" + b"\x00" * 92
    webm = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\x82\x84webm" + b"\x00" * 32
    for payload, signature, ext in ((avi, "avi/riff", ".avi"), (webm, "webm-mkv/ebml", ".webm")):
        polyglot = tmp_path / f"p{ext}.png"
        polyglot.write_bytes(sample_png + payload)
        info = detect_trailer.analyze(polyglot)
        assert info["detected_signature"] == signature
        out = extract.extract(polyglot, tmp_path / "out")
        assert out["extracted_video_path"].endswith(ext)


def test_appended_zip_is_reported_as_other_signature(sample_png):
    zip_like = b"PK\x03\x04" + b"\x00" * 60
    result = detect_trailer.analyze_bytes(sample_png + zip_like, "x")
    assert result["polyglot_status"] is False
    assert result["other_signature"] == "zip"
    assert "şüpheli" in result["analysis_summary"]


def test_extract_rejects_non_polyglot(tmp_path, sample_png):
    clean = tmp_path / "c.png"
    clean.write_bytes(sample_png)
    with pytest.raises(ValueError):
        extract.extract(clean, tmp_path / "out")
