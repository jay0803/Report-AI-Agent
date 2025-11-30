"""
KPI 청크 메타데이터 생성

청크에 검색/필터링용 메타데이터 추가
"""
from typing import Dict, Any, List


def build_kpi_metadata(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """
    KPI 청크에 메타데이터 추가
    
    Args:
        chunk: 청크 딕셔너리
        
    Returns:
        메타데이터 딕셔너리
    """
    metadata = {
        "dataset": "kpi",
        "source": chunk.get("source", "kpi_pdf"),
        "kpi_id": chunk.get("kpi_id", ""),
        "page_index": chunk.get("page_index", -1),
    }
    
    # 태그에서 추출
    tags = chunk.get("tags", [])
    if tags:
        # 첫 번째 태그를 kpi_name으로 (보통 KPI 이름)
        if len(tags) >= 1:
            metadata["kpi_name"] = tags[0]
        
        # 두 번째 태그를 category로
        if len(tags) >= 2:
            metadata["category"] = tags[1]
        
        # 세 번째 태그를 unit으로
        if len(tags) >= 3:
            metadata["unit"] = tags[2]
    
    # 키워드 (검색용) - Chroma는 리스트를 지원하지 않으므로 문자열로 변환
    metadata["keywords"] = ", ".join(tags) if tags else ""
    
    return metadata


def enhance_chunks_with_metadata(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    모든 청크에 메타데이터 추가
    
    Args:
        chunks: 청크 리스트
        
    Returns:
        메타데이터가 추가된 청크 리스트
    """
    enhanced_chunks = []
    
    for chunk in chunks:
        # 메타데이터 생성
        metadata = build_kpi_metadata(chunk)
        
        # 청크에 메타데이터 추가
        chunk["metadata"] = metadata
        enhanced_chunks.append(chunk)
    
    print(f"✅ 메타데이터 추가 완료: {len(enhanced_chunks)}개 청크")
    return enhanced_chunks


def get_metadata_summary(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    메타데이터 통계 요약
    
    Args:
        chunks: 메타데이터가 포함된 청크 리스트
        
    Returns:
        통계 정보 딕셔너리
    """
    summary = {
        "total_chunks": len(chunks),
        "categories": set(),
        "units": set(),
        "pages": set(),
        "kpi_names": set()
    }
    
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        
        if "category" in metadata and metadata["category"]:
            summary["categories"].add(metadata["category"])
        
        if "unit" in metadata and metadata["unit"]:
            summary["units"].add(metadata["unit"])
        
        if "page_index" in metadata:
            summary["pages"].add(metadata["page_index"])
        
        if "kpi_name" in metadata and metadata["kpi_name"]:
            summary["kpi_names"].add(metadata["kpi_name"])
    
    # set을 list로 변환
    summary["categories"] = sorted(list(summary["categories"]))
    summary["units"] = sorted(list(summary["units"]))
    summary["pages"] = sorted(list(summary["pages"]))
    summary["kpi_names"] = sorted(list(summary["kpi_names"]))
    
    summary["unique_categories"] = len(summary["categories"])
    summary["unique_units"] = len(summary["units"])
    summary["unique_pages"] = len(summary["pages"])
    summary["unique_kpi_names"] = len(summary["kpi_names"])
    
    return summary

