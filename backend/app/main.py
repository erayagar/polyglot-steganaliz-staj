"""FastAPI uygulama giriş noktası."""
import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.staticfiles import StaticFiles

from app import pipeline
from app.models import AnalyzeResponse, HealthResponse

app = FastAPI(
    title="Polyglot / Steganaliz Servisi",
    description="Görsel dosyaların arkasına gizlenmiş video/veri (polyglot) tespiti API'si.",
    version="0.1.0",
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "tmp"
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB

# Ayıklanan videolar (bkz. pipeline.run_pipeline) buradan /media/<dosya>
# yolunda tarayıcıya statik olarak sunulur.
pipeline.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=pipeline.MEDIA_DIR), name="media")

# Yalnızca PNG/JPEG kabul edilir; client'ın beyan ettiği Content-Type ile
# dosyanın gerçek magic bytes'ı çapraz doğrulanır (bkz. docs/format-notlari.md).
MAGIC_BYTES: dict[str, bytes] = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8",
}


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/v1/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED)
async def analyze(file: UploadFile = File(...)) -> AnalyzeResponse:
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
    saved_path = UPLOAD_DIR / saved_name
    saved_path.write_bytes(content)

    # CPU-yoğun analiz (trailer tarama, entropy, olası extraction) event
    # loop'u bloklamasın diye ayrı bir thread'de çalıştırılır.
    result = await asyncio.to_thread(pipeline.run_pipeline, saved_path)
    threat_score = pipeline.compute_threat_score(result)

    return AnalyzeResponse(
        polyglot_status=result["polyglot_status"],
        threat_score=threat_score,
        extracted_video_url=result["extracted_video_url"],
        analysis_summary=pipeline.build_analysis_summary(result, threat_score),
    )
