"""API yanıt/istek modelleri (Pydantic)."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class AnalyzeResponse(BaseModel):
    """Gün 14'te alanlar (threat_score hesabı, analysis_summary üretimi vb.)
    işlenecek; burada yalnızca şema iskeleti tanımlanır."""

    polyglot_status: bool
    threat_score: int | None = None
    extracted_video_url: str | None = None
    analysis_summary: str | None = None
