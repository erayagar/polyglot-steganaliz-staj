"""FastAPI uygulama giriş noktası."""
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status

from app.models import HealthResponse, UploadAck

app = FastAPI(
    title="Polyglot / Steganaliz Servisi",
    description="Görsel dosyaların arkasına gizlenmiş video/veri (polyglot) tespiti API'si.",
    version="0.1.0",
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "tmp"
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

# Yalnızca PNG/JPEG kabul edilir; client'ın beyan ettiği Content-Type ile
# dosyanın gerçek magic bytes'ı çapraz doğrulanır (bkz. docs/format-notlari.md).
MAGIC_BYTES: dict[str, bytes] = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8",
}


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/v1/analyze", response_model=UploadAck, status_code=status.HTTP_201_CREATED)
async def analyze(file: UploadFile = File(...)) -> UploadAck:
    signature = MAGIC_BYTES.get(file.content_type or "")
    if signature is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Desteklenmeyen dosya türü: '{file.content_type}'. "
                f"Yalnızca {', '.join(MAGIC_BYTES)} kabul edilir."
            ),
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Dosya çok büyük: {len(content)} bayt (üst sınır {MAX_UPLOAD_SIZE} bayt).",
        )

    if not content.startswith(signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya içeriği beyan edilen Content-Type ile uyuşmuyor (magic bytes doğrulaması başarısız).",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = ".png" if file.content_type == "image/png" else ".jpg"
    saved_name = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / saved_name).write_bytes(content)

    return UploadAck(
        filename=file.filename or "unknown",
        content_type=file.content_type,
        size_bytes=len(content),
        saved_as=saved_name,
    )
