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


class UploadAck(BaseModel):
    """Gün 12: yükleme kabul edildiğinde dönen geçici onay yanıtı.

    Gün 13'te bu endpoint analiz pipeline'ına bağlanınca yerini
    `AnalyzeResponse`e bırakacak.
    """

    filename: str
    content_type: str
    size_bytes: int
    saved_as: str
