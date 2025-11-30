"""
KPI 문서 처리를 위한 Pydantic 스키마

Raw JSON 스키마: Vision API로부터 받는 원본 구조
Canonical 스키마: 정규화된 KPI 데이터
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ========================================
# Raw JSON 스키마 (Vision API 구조화 대상)
# ========================================

class KPIRawItem(BaseModel):
    """페이지 내 개별 KPI 항목"""
    kpi_name: str = Field(default="", description="KPI 이름")
    category: str = Field(default="", description="KPI 카테고리")
    unit: str = Field(default="", description="단위")
    values: str = Field(default="", description="값")
    delta: str = Field(default="", description="증감")
    설명: str = Field(default="", description="설명")


class KPIPage(BaseModel):
    """PDF 페이지 단위 데이터"""
    page_index: int = Field(..., description="페이지 인덱스 (0부터 시작)")
    kpi_items: List[KPIRawItem] = Field(default_factory=list, description="KPI 항목 리스트", alias="KPI_항목")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="표 데이터", alias="표")
    text_summary: str = Field(default="", description="페이지 텍스트 요약", alias="텍스트요약")
    error: Optional[str] = Field(default=None, description="파싱 오류 메시지")
    
    class Config:
        populate_by_name = True  # alias와 field name 둘 다 허용


class KPIRawDocument(BaseModel):
    """전체 KPI 문서 (Raw JSON)"""
    title: str = Field(default="보험사 KPI 자료", description="문서 제목", alias="문서제목")
    total_pages: int = Field(..., description="총 페이지 수", alias="총페이지수")
    pages: List[KPIPage] = Field(default_factory=list, description="페이지 리스트")
    
    class Config:
        populate_by_name = True


# ========================================
# Canonical 스키마 (정규화된 KPI)
# ========================================

class CanonicalKPI(BaseModel):
    """정규화된 KPI 데이터"""
    kpi_id: str = Field(..., description="KPI 고유 ID (UUID)")
    page_index: int = Field(..., description="원본 페이지 인덱스")
    kpi_name: str = Field(..., description="KPI 이름")
    category: str = Field(default="", description="KPI 카테고리")
    unit: str = Field(default="", description="단위")
    values: str = Field(default="", description="값")
    delta: str = Field(default="", description="증감")
    description: str = Field(default="", description="설명")
    table: Optional[Dict[str, Any] | List[Any]] = Field(default=None, description="연관 표 데이터")
    raw_text_summary: str = Field(default="", description="페이지 텍스트 요약")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


# ========================================
# 청크 스키마
# ========================================

class KPIChunk(BaseModel):
    """KPI 청크 데이터"""
    chunk_id: str = Field(..., description="청크 고유 ID (UUID)")
    kpi_id: str = Field(..., description="원본 KPI ID")
    page_index: int = Field(..., description="페이지 인덱스")
    text: str = Field(..., description="임베딩용 텍스트")
    source: str = Field(default="kpi_pdf", description="데이터 소스")
    tags: List[str] = Field(default_factory=list, description="검색용 태그")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

