"""FastAPI uygulama giriş noktası."""
import asyncio
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import pipeline
from app.models import AnalyzeResponse, HealthResponse

logger = logging.getLogger("app")

app = FastAPI(
    title="Polyglot / Steganaliz Servisi",
    description="Görsel dosyaların arkasına gizlenmiş video/veri (polyglot) tespiti API'si.",
    version="0.1.0",
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "tmp"
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB
# multipart sınırları/başlıkları için dosya boyutunun üstüne tanınan pay
MULTIPART_OVERHEAD = 64 * 1024
READ_CHUNK_SIZE = 1024 * 1024
# Ayıklanan videolar bu süreden sonra media/ dizininden silinir.
MEDIA_TTL_SECONDS = 60 * 60

# Ayıklanan videolar (bkz. pipeline.run_pipeline) buradan /media/<dosya>
# yolunda tarayıcıya statik olarak sunulur.
pipeline.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=pipeline.MEDIA_DIR), name="media")

# Yalnızca PNG/JPEG kabul edilir. Format dosyanın gerçek magic bytes'ından
# belirlenir; client'ın beyan ettiği Content-Type yalnızca PNG/JPEG
# olduğunda gerçek formatla çapraz doğrulanır (bkz. docs/format-notlari.md).
MAGIC_BYTES: dict[str, bytes] = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8",
}
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg"}


def _too_large_detail(size: int) -> str:
    return f"Dosya çok büyük: {size} bayt (üst sınır {MAX_UPLOAD_SIZE} bayt)."


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Content-Length üst sınırı aşan istekleri gövde okunmadan (multipart
    parse edilip diske yazılmadan önce) 413 ile reddeder."""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_SIZE + MULTIPART_OVERHEAD:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": _too_large_detail(int(content_length))},
        )
    return await call_next(request)


# frontend/ backend'den farklı bir origin'den (file://, python -m http.server
# vb.) açılabildiği ve servis kimlik doğrulama/cookie kullanmadığı için tüm
# origin'lere izin verilmesi (yalnızca geliştirme ortamı için) yeterlidir.
# En son eklenen middleware en dışta çalıştığından CORS, limit_upload_size'dan
# sonra eklenir; böylece 413 yanıtları da CORS başlığı taşır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Beklenmeyen (öngörülmemiş) hataları 500 yerine anlamlı, stack-trace
    sızdırmayan bir JSON gövdesiyle döndürür."""
    logger.exception("Beklenmeyen hata: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Sunucuda beklenmeyen bir hata oluştu."},
    )


def _detect_mime(content: bytes) -> str | None:
    for mime, signature in MAGIC_BYTES.items():
        if content.startswith(signature):
            return mime
    return None


def _purge_old_media() -> None:
    """`MEDIA_TTL_SECONDS`'tan eski ayıklanmış videoları siler."""
    cutoff = time.time() - MEDIA_TTL_SECONDS
    for media_file in pipeline.MEDIA_DIR.glob("*"):
        try:
            if media_file.is_file() and media_file.stat().st_mtime < cutoff:
                media_file.unlink()
        except OSError:
            logger.warning("Eski media dosyası silinemedi: %s", media_file)


def _analyze_and_cleanup(saved_path: Path) -> dict:
    """Pipeline'ı çalıştırır; sonuç ne olursa olsun yüklenen geçici dosyayı
    siler ve süresi dolmuş media dosyalarını temizler."""
    try:
        return pipeline.run_pipeline(saved_path)
    finally:
        saved_path.unlink(missing_ok=True)
        _purge_old_media()


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Servisin ayakta olduğunu doğrulayan basit health-check endpoint'i."""
    return HealthResponse(status="ok")


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)) -> AnalyzeResponse:
    """Yüklenen PNG/JPEG dosyasını doğrulayıp (magic bytes + boyut), tam
    steganaliz pipeline'ından (`pipeline.run_pipeline`) geçirir ve
    polyglot durumu, tehdit skoru ve varsa ayıklanan video URL'ini döner."""
    if file.size is not None and file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=_too_large_detail(file.size))

    # Content-Length gönderilmeyen (chunked) isteklerde de sınırın aşılıp
    # aşılmadığını anlamak için en fazla MAX_UPLOAD_SIZE + 1 bayt okunur.
    chunks: list[bytes] = []
    total = 0
    while total <= MAX_UPLOAD_SIZE:
        chunk = await file.read(min(READ_CHUNK_SIZE, MAX_UPLOAD_SIZE + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    content = b"".join(chunks)

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yüklenen dosya boş (0 bayt).",
        )

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Dosya çok büyük: üst sınır {MAX_UPLOAD_SIZE} bayt.",
        )

    actual_mime = _detect_mime(content)
    if actual_mime is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Desteklenmeyen dosya türü (beyan edilen: '{file.content_type}'). "
                f"Yalnızca {', '.join(MAGIC_BYTES)} kabul edilir."
            ),
        )

    if file.content_type in MAGIC_BYTES and file.content_type != actual_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya içeriği beyan edilen Content-Type ile uyuşmuyor (magic bytes doğrulaması başarısız).",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{EXTENSIONS[actual_mime]}"
    await asyncio.to_thread(saved_path.write_bytes, content)

    # CPU-yoğun analiz (trailer tarama, entropy, olası extraction) event
    # loop'u bloklamasın diye ayrı bir thread'de çalıştırılır.
    try:
        result = await asyncio.to_thread(_analyze_and_cleanup, saved_path)
    except ValueError as exc:
        # scripts/ altındaki tüm analiz modülleri bozuk/geçersiz dosya
        # yapısında ValueError fırlatır (bkz. detect_trailer.py, size_analysis.py).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Dosya işlenemedi (bozuk veya geçersiz içerik): {exc}",
        ) from exc

    threat_score = pipeline.compute_threat_score(result)

    return AnalyzeResponse(
        polyglot_status=result["polyglot_status"],
        threat_score=threat_score,
        extracted_video_url=result["extracted_video_url"],
        analysis_summary=pipeline.build_analysis_summary(result, threat_score),
    )
