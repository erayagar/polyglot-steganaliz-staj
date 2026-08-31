"""FastAPI uygulama giriş noktası."""
from fastapi import FastAPI

from app.models import HealthResponse

app = FastAPI(
    title="Polyglot / Steganaliz Servisi",
    description="Görsel dosyaların arkasına gizlenmiş video/veri (polyglot) tespiti API'si.",
    version="0.1.0",
)


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
