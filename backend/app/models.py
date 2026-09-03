"""API yanıt/istek modelleri (Pydantic)."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class AnalyzeResponse(BaseModel):
    """`/api/v1/analyze` yanıt şeması.

    `threat_score` (0-100), trailer tespiti + entropy farkı + boyut sapması
    sinyallerinin ağırlıklı birleşimiyle `pipeline.compute_threat_score`
    tarafından hesaplanır (bkz. docs/gun14-json-yanit-semasi-raporu.md).
    """

    polyglot_status: bool
    threat_score: int
    extracted_video_url: str | None = None
    analysis_summary: str
