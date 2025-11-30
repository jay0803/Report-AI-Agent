"""
통합 Canonical 문서 스키마

모든 문서 타입(일일/주간/월간/실적 보고서, KPI, 템플릿)을 
단일 형식으로 표준화하여 RAG 검색 및 Agent 처리를 단순화

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Optional, Dict, Any, Literal
from datetime import date
from pydantic import BaseModel, Field


# ========================================
# 문서 섹션 스키마
# ========================================

class TaskSection(BaseModel):
    """작업 섹션"""
    task_id: Optional[str] = Field(None, description="작업 ID")
    title: str = Field(..., description="작업 제목")
    description: str = Field("", description="작업 설명")
    time_start: Optional[str] = Field(None, description="시작 시간")
    time_end: Optional[str] = Field(None, description="종료 시간")
    status: Optional[str] = Field(None, description="상태")
    note: str = Field("", description="비고")


class KPISection(BaseModel):
    """KPI 섹션"""
    kpi_name: str = Field(..., description="KPI 이름")
    value: str = Field("", description="값")
    unit: Optional[str] = Field(None, description="단위")
    category: Optional[str] = Field(None, description="카테고리")
    delta: Optional[str] = Field(None, description="증감")
    description: str = Field("", description="설명")
    note: str = Field("", description="비고")


class DocumentSections(BaseModel):
    """
    문서 섹션 컨테이너
    
    각 문서 타입에 따라 일부 섹션만 채워짐:
    - 일일 보고서: tasks, issues, plans
    - KPI 문서: kpis
    - 월간 보고서: tasks, kpis, issues, plans
    """
    tasks: List[TaskSection] = Field(default_factory=list, description="작업 목록")
    kpis: List[KPISection] = Field(default_factory=list, description="KPI 목록")
    issues: List[str] = Field(default_factory=list, description="이슈/문제사항")
    plans: List[str] = Field(default_factory=list, description="계획사항")
    summary: str = Field("", description="전체 요약")


# ========================================
# 통합 Canonical 스키마
# ========================================

class UnifiedCanonical(BaseModel):
    """
    통합 Canonical 문서 스키마
    
    모든 문서 타입을 단일 형식으로 통합하여 다음을 지원:
    - 일관된 Chroma 저장 구조
    - Agent의 단순화된 retrieval 로직
    - 확장 가능한 메타데이터 구조
    
    사용 예:
        - 일일 보고서 → doc_type="daily", sections.tasks 채움
        - KPI 문서 → doc_type="kpi", sections.kpis 채움
        - 템플릿 → doc_type="template", raw_text만 채움
    """
    
    # 필수 필드
    doc_id: str = Field(..., description="문서 고유 ID (UUID 또는 deterministic hash)")
    doc_type: Literal["daily", "weekly", "monthly", "performance", "kpi", "template"] = Field(
        ..., 
        description="문서 타입"
    )
    title: str = Field(..., description="문서 제목")
    
    # 날짜 관련
    single_date: Optional[date] = Field(None, description="단일 날짜 (일일 보고서)")
    period_start: Optional[date] = Field(None, description="시작 날짜 (주간/월간)")
    period_end: Optional[date] = Field(None, description="종료 날짜 (주간/월간)")
    
    # 작성자
    owner: str = Field("", description="작성자/담당자")
    
    # 원본 텍스트 (검색용)
    raw_text: str = Field("", description="전체 원본 텍스트 (검색 fallback)")
    
    # 구조화된 섹션
    sections: DocumentSections = Field(
        default_factory=DocumentSections,
        description="구조화된 문서 섹션"
    )
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="""
        추가 메타데이터:
        - source_file: 원본 파일 경로
        - page_index: KPI 페이지 번호
        - chunk_count: 생성된 청크 수
        - processing_date: 처리 일자
        - original_format: 원본 포맷 (report|kpi|template)
        기타 문서 타입별 커스텀 필드
        """
    )


# ========================================
# 청크 메타데이터 스키마
# ========================================

class UnifiedChunkMetadata(BaseModel):
    """
    통합 청크 메타데이터
    
    Chroma에 저장되는 청크의 메타데이터 형식을 표준화
    """
    # 문서 정보
    doc_id: str = Field(..., description="원본 문서 ID")
    doc_type: str = Field(..., description="문서 타입")
    
    # 청크 정보
    chunk_type: str = Field(..., description="청크 타입 (task|kpi|issue|plan|summary)")
    chunk_id: str = Field(..., description="청크 ID")
    
    # 날짜 정보 (문자열로 저장, Chroma 필터링용)
    date: Optional[str] = Field(None, description="날짜 (YYYY-MM-DD)")
    period_start: Optional[str] = Field(None, description="시작 날짜")
    period_end: Optional[str] = Field(None, description="종료 날짜")
    
    # 작성자
    owner: str = Field("", description="작성자")
    
    # 소스 정보
    source_file: Optional[str] = Field(None, description="원본 파일")
    
    # 청크 분할 정보
    part: Optional[int] = Field(None, description="분할 청크 번호")
    total_parts: Optional[int] = Field(None, description="전체 분할 수")
    
    # 추가 메타데이터
    extra: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

