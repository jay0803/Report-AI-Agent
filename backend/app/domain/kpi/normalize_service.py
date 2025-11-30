"""
KPI Raw JSON → CanonicalKPI 정규화 서비스
"""
import uuid
from typing import List

from app.domain.kpi.schemas import KPIRawDocument, CanonicalKPI, KPIPage, KPIRawItem


def normalize_kpi_document(raw_doc: KPIRawDocument) -> List[CanonicalKPI]:
    """
    KPIRawDocument를 CanonicalKPI 리스트로 정규화
    
    Args:
        raw_doc: Vision API로부터 받은 원본 문서
        
    Returns:
        CanonicalKPI 리스트
    """
    canonical_kpis = []
    
    for page in raw_doc.pages:
        # 오류 페이지는 건너뛰기
        if page.error:
            print(f"⚠️  페이지 {page.page_index + 1} 건너뛰기 (오류: {page.error})")
            continue
        
        # KPI 항목 변환
        for kpi_item in page.kpi_items:
            canonical_kpi = _normalize_kpi_item(
                kpi_item=kpi_item,
                page_index=page.page_index,
                text_summary=page.text_summary,
                tables=page.tables
            )
            canonical_kpis.append(canonical_kpi)
        
        # 표만 있고 KPI 항목이 없는 경우 처리
        if not page.kpi_items and page.tables:
            for idx, table in enumerate(page.tables):
                table_kpi = _create_table_kpi(
                    table=table,
                    page_index=page.page_index,
                    table_index=idx,
                    text_summary=page.text_summary
                )
                canonical_kpis.append(table_kpi)
    
    print(f"✅ 정규화 완료: {len(canonical_kpis)}개 CanonicalKPI 생성")
    return canonical_kpis


def _normalize_kpi_item(
    kpi_item: KPIRawItem,
    page_index: int,
    text_summary: str,
    tables: List
) -> CanonicalKPI:
    """
    개별 KPIRawItem을 CanonicalKPI로 변환
    
    Args:
        kpi_item: 원본 KPI 항목
        page_index: 페이지 인덱스
        text_summary: 페이지 텍스트 요약
        tables: 페이지 표 데이터
        
    Returns:
        CanonicalKPI 객체
    """
    # 설명 구성: 원본 설명 + 필요시 요약 추가
    description = kpi_item.설명
    if not description and text_summary:
        description = text_summary[:200]  # 최대 200자
    
    # 연관 표 찾기 (kpi_name이 표에 포함되어 있는지 간단히 체크)
    related_table = None
    if tables and kpi_item.kpi_name:
        for table in tables:
            table_str = str(table).lower()
            if kpi_item.kpi_name.lower() in table_str:
                related_table = table
                break
    
    return CanonicalKPI(
        kpi_id=str(uuid.uuid4()),
        page_index=page_index,
        kpi_name=kpi_item.kpi_name,
        category=kpi_item.category,
        unit=kpi_item.unit,
        values=kpi_item.values,
        delta=kpi_item.delta,
        description=description,
        table=related_table,
        raw_text_summary=text_summary,
        metadata={}
    )


def _create_table_kpi(
    table: dict | list,
    page_index: int,
    table_index: int,
    text_summary: str
) -> CanonicalKPI:
    """
    표 데이터만 있는 경우 CanonicalKPI 생성
    
    Args:
        table: 표 데이터
        page_index: 페이지 인덱스
        table_index: 표 인덱스
        text_summary: 페이지 텍스트 요약
        
    Returns:
        CanonicalKPI 객체
    """
    return CanonicalKPI(
        kpi_id=str(uuid.uuid4()),
        page_index=page_index,
        kpi_name=f"표_{page_index + 1}_{table_index + 1}",
        category="표",
        unit="",
        values="",
        delta="",
        description=text_summary[:200] if text_summary else "",
        table=table,
        raw_text_summary=text_summary,
        metadata={}
    )


def get_normalization_stats(canonical_kpis: List[CanonicalKPI]) -> dict:
    """
    정규화 통계 정보 반환
    
    Args:
        canonical_kpis: CanonicalKPI 리스트
        
    Returns:
        통계 정보 딕셔너리
    """
    stats = {
        "total_kpis": len(canonical_kpis),
        "by_category": {},
        "with_table": 0,
        "with_delta": 0,
        "pages": set()
    }
    
    for kpi in canonical_kpis:
        # 카테고리별 카운트
        category = kpi.category if kpi.category else "미분류"
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        # 표 있는 KPI
        if kpi.table:
            stats["with_table"] += 1
        
        # 증감 정보 있는 KPI
        if kpi.delta:
            stats["with_delta"] += 1
        
        # 페이지 추적
        stats["pages"].add(kpi.page_index)
    
    stats["total_pages"] = len(stats["pages"])
    stats["pages"] = sorted(list(stats["pages"]))
    
    return stats

