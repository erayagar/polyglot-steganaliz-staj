import pytest
from fastapi.testclient import TestClient

from app import main, pipeline


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(pipeline, "MEDIA_DIR", tmp_path / "media")
    return TestClient(main.app, raise_server_exceptions=False)


def _post(client, content: bytes, content_type: str = "image/png", name: str = "x.png"):
    return client.post("/api/v1/analyze", files={"file": (name, content, content_type)})


def test_health(client):
    assert client.get("/").json() == {"status": "ok"}


def test_polyglot_is_detected_and_extracted(client, tmp_path, sample_png, sample_mp4):
    response = _post(client, sample_png + sample_mp4)
    assert response.status_code == 200
    body = response.json()
    assert body["polyglot_status"] is True
    assert body["threat_score"] >= 60
    video_name = body["extracted_video_url"].removeprefix("/media/")
    assert (tmp_path / "media" / video_name).read_bytes() == sample_mp4


def test_clean_jpeg_is_clean(client, sample_jpg):
    response = _post(client, sample_jpg, "image/jpeg", "x.jpg")
    assert response.status_code == 200
    assert response.json()["polyglot_status"] is False
    assert response.json()["threat_score"] == 0


def test_upload_is_deleted_after_analysis(client, tmp_path, sample_png):
    assert _post(client, sample_png).status_code == 200
    assert list((tmp_path / "uploads").iterdir()) == []


def test_generic_content_type_is_accepted_by_magic_bytes(client, sample_png):
    assert _post(client, sample_png, "application/octet-stream").status_code == 200


def test_declared_type_mismatch_is_rejected(client, sample_png):
    assert _post(client, sample_png, "image/jpeg").status_code == 400


def test_unsupported_format_is_rejected(client):
    assert _post(client, b"GIF89a" + b"\x00" * 32, "image/gif", "x.gif").status_code == 400


def test_empty_file_is_rejected(client):
    assert _post(client, b"").status_code == 400


def test_too_large_file_is_rejected(client, monkeypatch, sample_png):
    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE", len(sample_png) - 1)
    assert _post(client, sample_png).status_code == 413


def test_oversized_content_length_is_rejected_before_parsing(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE", 10)
    monkeypatch.setattr(main, "MULTIPART_OVERHEAD", 0)
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("x.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        headers={"Origin": "http://127.0.0.1:5500"},
    )
    assert response.status_code == 413
    # Frontend hata mesajını okuyabilsin diye 413 de CORS başlığı taşımalı.
    assert response.headers.get("access-control-allow-origin") == "*"


@pytest.mark.parametrize(
    "content",
    [
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 20,  # IEND yok
        b"\xff\xd8\xff",  # tek 0xFF ile biten JPEG
        b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x10\x00\x10\x00\xff\xd9",  # 0 kanal
    ],
)
def test_corrupt_files_return_422_not_500(client, content):
    content_type = "image/png" if content.startswith(b"\x89PNG") else "image/jpeg"
    assert _post(client, content, content_type).status_code == 422
