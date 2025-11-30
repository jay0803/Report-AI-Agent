"""
KPI 문서 처리 모듈

PDF → Vision → Raw JSON → Canonical → Chunks 파이프라인
"""
from app.domain.kpi.schemas import (
    KPIRawItem,
    KPIPage,
    KPIRawDocument,
    CanonicalKPI,
    KPIChunk
)
from app.domain.kpi.vision_service import KPIVisionService
from app.domain.kpi.normalize_service import normalize_kpi_document, get_normalization_stats
from app.domain.kpi.chunker import build_kpi_chunks, get_chunk_statistics
from app.domain.kpi.metadata import build_kpi_metadata, enhance_chunks_with_metadata, get_metadata_summary


__all__ = [
    # Schemas
    "KPIRawItem",
    "KPIPage",
    "KPIRawDocument",
    "CanonicalKPI",
    "KPIChunk",
    
    # Services
    "KPIVisionService",
    "normalize_kpi_document",
    "get_normalization_stats",
    "build_kpi_chunks",
    "get_chunk_statistics",
    "build_kpi_metadata",
    "enhance_chunks_with_metadata",
    "get_metadata_summary",
]

