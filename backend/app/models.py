"""API yanıt/istek modelleri (Pydantic)."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class AnalyzeResponse(BaseModel):
    """`/api/v1/analyze` yanıt şeması.

    Gün 13'te pipeline'a bağlandı (`polyglot_status`, `extracted_video_url`
    doluyor); `threat_score` ağırlıklı hesabı ve dinamik `analysis_summary`
    metni Gün 14'te işlenecek, bu yüzden ikisi de şimdilik opsiyonel.
    """

    polyglot_status: bool
    threat_score: int | None = None
    extracted_video_url: str | None = None
    analysis_summary: str | None = None
