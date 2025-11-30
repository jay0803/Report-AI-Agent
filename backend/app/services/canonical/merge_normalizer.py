"""
통합 Canonical 변환기

기존 분리된 Canonical 스키마들을 통합 UnifiedCanonical로 변환

변환 지원:
- ReportCanonical (daily/weekly/monthly) → UnifiedCanonical
- KPICanonical → UnifiedCanonical
- Raw PDF Text → UnifiedCanonical (템플릿용)

Author: AI Assistant
Created: 2025-11-18
"""
import hashlib
from typing import Dict, Any
from datetime import date

from app.domain.report.schemas import CanonicalReport, TaskItem, KPIItem
from app.domain.kpi.schemas import CanonicalKPI
from app.domain.common.canonical_schema import (
    UnifiedCanonical,
    DocumentSections,
    TaskSection,
    KPISection
)


# ========================================
# ID 생성 유틸리티
# ========================================

def generate_doc_id(*parts: str) -> str:
    """
    결정적(deterministic) 문서 ID 생성
    
    동일한 문서에 대해 항상 동일한 ID를 생성하여
    재실행 시 중복을 방지합니다.
    
    Args:
        *parts: ID 생성에 사용할 문자열들
        
    Returns:
        SHA256 해시 기반 ID (32자)
    """
    combined = "|".join(str(p) for p in parts)
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


# ========================================
# Report Canonical → Unified Canonical
# ========================================

def report_to_unified(canonical_report: CanonicalReport) -> UnifiedCanonical:
    """
    기존 ReportCanonical을 UnifiedCanonical로 변환
    
    Args:
        canonical_report: 기존 보고서 Canonical 객체
        
    Returns:
        UnifiedCanonical 객체
        
    Example:
        >>> report = CanonicalReport(...)
        >>> unified = report_to_unified(report)
        >>> unified.doc_type  # "daily"
    """
    # 문서 ID 생성 (deterministic)
    doc_id = canonical_report.report_id
    
    # 문서 타입
    doc_type = canonical_report.report_type
    
    # 제목 생성
    title_map = {
        "daily": "일일 업무 보고서",
        "weekly": "주간 업무 보고서",
        "monthly": "월간 업무 보고서"
    }
    title = title_map.get(doc_type, "업무 보고서")
    
    # 날짜 처리
    # 일일 보고서: date 필드 사용
    # 주간/월간: period_start, period_end 사용
    doc_date = None
    period_start = None
    period_end = None
    
    if doc_type == "daily":
        doc_date = canonical_report.period_start
    else:
        period_start = canonical_report.period_start
        period_end = canonical_report.period_end
    
    # Tasks 변환
    tasks = [
        TaskSection(
            task_id=task.task_id,
            title=task.title,
            description=task.description,
            time_start=task.time_start,
            time_end=task.time_end,
            status=task.status,
            note=task.note
        )
        for task in canonical_report.tasks
    ]
    
    # KPIs 변환
    kpis = [
        KPISection(
            kpi_name=kpi.kpi_name,
            value=kpi.value,
            unit=kpi.unit,
            category=kpi.category,
            delta=None,  # Report KPI에는 delta 없음
            description="",
            note=kpi.note
        )
        for kpi in canonical_report.kpis
    ]
    
    # Sections 생성
    sections = DocumentSections(
        tasks=tasks,
        kpis=kpis,
        issues=canonical_report.issues.copy(),
        plans=canonical_report.plans.copy(),
        summary=_generate_report_summary(canonical_report)
    )
    
    # Raw text 생성 (검색용)
    raw_text = _generate_report_raw_text(canonical_report)
    
    # 메타데이터 복사 및 추가
    metadata = canonical_report.metadata.copy()
    metadata["original_format"] = "report"
    metadata["original_report_id"] = canonical_report.report_id
    
    return UnifiedCanonical(
        doc_id=doc_id,
        doc_type=doc_type,
        title=title,
        single_date=doc_date,
        period_start=period_start,
        period_end=period_end,
        owner=canonical_report.owner,
        raw_text=raw_text,
        sections=sections,
        metadata=metadata
    )


def _generate_report_summary(canonical: CanonicalReport) -> str:
    """보고서 요약 텍스트 생성"""
    lines = []
    
    if canonical.tasks:
        lines.append(f"총 {len(canonical.tasks)}건의 작업")
    
    if canonical.kpis:
        lines.append(f"KPI {len(canonical.kpis)}개 항목")
    
    if canonical.issues:
        lines.append(f"이슈 {len(canonical.issues)}건")
    
    if canonical.plans:
        lines.append(f"계획 {len(canonical.plans)}건")
    
    return ", ".join(lines) if lines else "업무 보고서"


def _generate_report_raw_text(canonical: CanonicalReport) -> str:
    """보고서 전체 텍스트 생성 (검색용)"""
    parts = []
    
    # 작성자 및 날짜
    if canonical.owner:
        parts.append(f"작성자: {canonical.owner}")
    
    if canonical.period_start:
        parts.append(f"날짜: {canonical.period_start.isoformat()}")
    
    # Tasks
    if canonical.tasks:
        parts.append("\n=== 작업 목록 ===")
        for task in canonical.tasks:
            task_text = f"- {task.title}"
            if task.description:
                task_text += f": {task.description}"
            if task.time_start and task.time_end:
                task_text += f" ({task.time_start}~{task.time_end})"
            parts.append(task_text)
    
    # KPIs
    if canonical.kpis:
        parts.append("\n=== KPI ===")
        for kpi in canonical.kpis:
            kpi_text = f"- {kpi.kpi_name}: {kpi.value}"
            if kpi.unit:
                kpi_text += f" {kpi.unit}"
            parts.append(kpi_text)
    
    # Issues
    if canonical.issues:
        parts.append("\n=== 이슈 ===")
        for issue in canonical.issues:
            parts.append(f"- {issue}")
    
    # Plans
    if canonical.plans:
        parts.append("\n=== 계획 ===")
        for plan in canonical.plans:
            parts.append(f"- {plan}")
    
    return "\n".join(parts)


# ========================================
# KPI Canonical → Unified Canonical
# ========================================

def kpi_to_unified(canonical_kpi: CanonicalKPI) -> UnifiedCanonical:
    """
    기존 KPI Canonical을 UnifiedCanonical로 변환
    
    Args:
        canonical_kpi: 기존 KPI Canonical 객체
        
    Returns:
        UnifiedCanonical 객체
        
    Example:
        >>> kpi = CanonicalKPI(...)
        >>> unified = kpi_to_unified(kpi)
        >>> unified.doc_type  # "kpi"
    """
    # 문서 ID
    doc_id = canonical_kpi.kpi_id
    
    # KPI 섹션 생성
    kpi_section = KPISection(
        kpi_name=canonical_kpi.kpi_name,
        value=canonical_kpi.values,
        unit=canonical_kpi.unit,
        category=canonical_kpi.category,
        delta=canonical_kpi.delta,
        description=canonical_kpi.description,
        note=""
    )
    
    sections = DocumentSections(
        kpis=[kpi_section],
        summary=canonical_kpi.raw_text_summary
    )
    
    # Raw text 생성
    raw_text = _generate_kpi_raw_text(canonical_kpi)
    
    # 메타데이터
    metadata = canonical_kpi.metadata.copy()
    metadata["original_format"] = "kpi"
    metadata["original_kpi_id"] = canonical_kpi.kpi_id
    metadata["page_index"] = canonical_kpi.page_index
    
    # 표 데이터 추가
    if canonical_kpi.table:
        metadata["table"] = canonical_kpi.table
    
    return UnifiedCanonical(
        doc_id=doc_id,
        doc_type="kpi",
        title=f"KPI: {canonical_kpi.kpi_name}",
        single_date=None,
        period_start=None,
        period_end=None,
        owner="",
        raw_text=raw_text,
        sections=sections,
        metadata=metadata
    )


def _generate_kpi_raw_text(canonical: CanonicalKPI) -> str:
    """KPI 전체 텍스트 생성 (검색용)"""
    parts = [
        f"KPI: {canonical.kpi_name}",
        f"카테고리: {canonical.category}",
        f"값: {canonical.values}",
    ]
    
    if canonical.unit:
        parts.append(f"단위: {canonical.unit}")
    
    if canonical.delta:
        parts.append(f"증감: {canonical.delta}")
    
    if canonical.description:
        parts.append(f"설명: {canonical.description}")
    
    if canonical.raw_text_summary:
        parts.append(f"\n{canonical.raw_text_summary}")
    
    return "\n".join(parts)


# ========================================
# Raw Text → Unified Canonical (템플릿용)
# ========================================

def text_to_unified(
    text: str,
    title: str,
    source_file: str = "",
    doc_type: str = "template"
) -> UnifiedCanonical:
    """
    Raw Text를 UnifiedCanonical로 변환 (템플릿 문서용)
    
    구조화되지 않은 텍스트 문서를 처리할 때 사용
    예: PDF 템플릿, 매뉴얼 등
    
    Args:
        text: 원본 텍스트
        title: 문서 제목
        source_file: 원본 파일 경로
        doc_type: 문서 타입 (기본값: "template")
        
    Returns:
        UnifiedCanonical 객체
    """
    # 문서 ID 생성
    doc_id = generate_doc_id(doc_type, title, source_file)
    
    # 빈 섹션 (구조화되지 않은 문서)
    sections = DocumentSections()
    
    # 메타데이터
    metadata = {
        "original_format": "text",
        "source_file": source_file
    }
    
    return UnifiedCanonical(
        doc_id=doc_id,
        doc_type=doc_type,
        title=title,
        single_date=None,
        period_start=None,
        period_end=None,
        owner="",
        raw_text=text,
        sections=sections,
        metadata=metadata
    )


# ========================================
# 배치 변환 헬퍼
# ========================================

def batch_convert_reports(
    canonical_reports: list[CanonicalReport]
) -> list[UnifiedCanonical]:
    """
    여러 보고서를 한 번에 변환
    
    Args:
        canonical_reports: CanonicalReport 리스트
        
    Returns:
        UnifiedCanonical 리스트
    """
    return [report_to_unified(report) for report in canonical_reports]


def batch_convert_kpis(
    canonical_kpis: list[CanonicalKPI]
) -> list[UnifiedCanonical]:
    """
    여러 KPI를 한 번에 변환
    
    Args:
        canonical_kpis: CanonicalKPI 리스트
        
    Returns:
        UnifiedCanonical 리스트
    """
    return [kpi_to_unified(kpi) for kpi in canonical_kpis]

