"""
KPI 청킹 유틸리티

CanonicalKPI를 RAG용 청크로 변환
"""
import uuid
import json
from typing import List, Dict, Any

from app.domain.kpi.schemas import CanonicalKPI


def build_kpi_chunks(kpis: List[CanonicalKPI]) -> List[Dict[str, Any]]:
    """
    CanonicalKPI 리스트를 청크 리스트로 변환
    
    Args:
        kpis: CanonicalKPI 리스트
        
    Returns:
        청크 딕셔너리 리스트
    """
    chunks = []
    
    for kpi in kpis:
        chunk = _create_kpi_chunk(kpi)
        chunks.append(chunk)
    
    print(f"✅ 청킹 완료: {len(chunks)}개 청크 생성")
    return chunks


def _create_kpi_chunk(kpi: CanonicalKPI) -> Dict[str, Any]:
    """
    개별 CanonicalKPI를 청크로 변환
    
    Args:
        kpi: CanonicalKPI 객체
        
    Returns:
        청크 딕셔너리
    """
    # 텍스트 구성
    text_parts = []
    
    # KPI 이름
    if kpi.kpi_name:
        text_parts.append(f"[KPI] {kpi.kpi_name}")
    
    # 카테고리
    if kpi.category:
        text_parts.append(f"카테고리: {kpi.category}")
    
    # 값 + 단위
    if kpi.values:
        if kpi.unit:
            text_parts.append(f"값: {kpi.values} ({kpi.unit})")
        else:
            text_parts.append(f"값: {kpi.values}")
    
    # 증감
    if kpi.delta:
        text_parts.append(f"증감: {kpi.delta}")
    
    # 설명
    if kpi.description:
        text_parts.append(f"\n설명: {kpi.description}")
    
    # 표 데이터 (flatten to text)
    if kpi.table:
        table_text = _flatten_table(kpi.table)
        if table_text:
            text_parts.append(f"\n[표 데이터]\n{table_text}")
    
    # 텍스트 요약
    if kpi.raw_text_summary and kpi.raw_text_summary not in text_parts:
        text_parts.append(f"\n페이지 요약: {kpi.raw_text_summary}")
    
    text = "\n".join(text_parts)
    
    # 태그 생성
    tags = []
    if kpi.kpi_name:
        tags.append(kpi.kpi_name)
    if kpi.category:
        tags.append(kpi.category)
    if kpi.unit:
        tags.append(kpi.unit)
    
    # 청크 생성
    chunk = {
        "chunk_id": str(uuid.uuid4()),
        "kpi_id": kpi.kpi_id,
        "page_index": kpi.page_index,
        "text": text,
        "source": "kpi_pdf",
        "tags": tags,
        "metadata": {}  # metadata.py에서 채움
    }
    
    return chunk


def _flatten_table(table: Dict[str, Any] | List[Any]) -> str:
    """
    표 데이터를 텍스트로 flatten
    
    Args:
        table: 표 데이터 (dict 또는 list)
        
    Returns:
        flatten된 텍스트
    """
    try:
        if isinstance(table, dict):
            # dict 형태의 표
            lines = []
            for key, value in table.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                lines.append(f"{key}: {value_str}")
            return "\n".join(lines)
        
        elif isinstance(table, list):
            # list 형태의 표
            lines = []
            for idx, item in enumerate(table):
                if isinstance(item, dict):
                    item_str = ", ".join([f"{k}: {v}" for k, v in item.items()])
                else:
                    item_str = str(item)
                lines.append(f"[{idx + 1}] {item_str}")
            return "\n".join(lines)
        
        else:
            return str(table)
    
    except Exception as e:
        print(f"⚠️  표 flatten 오류: {e}")
        return str(table)


def get_chunk_statistics(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    청크 통계 정보 반환
    
    Args:
        chunks: 청크 리스트
        
    Returns:
        통계 정보 딕셔너리
    """
    stats = {
        "total_chunks": len(chunks),
        "avg_text_length": 0,
        "max_text_length": 0,
        "min_text_length": float('inf'),
        "pages": set(),
        "tags_count": {}
    }
    
    total_length = 0
    
    for chunk in chunks:
        # 텍스트 길이 통계
        text_length = len(chunk["text"])
        total_length += text_length
        stats["max_text_length"] = max(stats["max_text_length"], text_length)
        stats["min_text_length"] = min(stats["min_text_length"], text_length)
        
        # 페이지 추적
        stats["pages"].add(chunk["page_index"])
        
        # 태그 카운트
        for tag in chunk.get("tags", []):
            stats["tags_count"][tag] = stats["tags_count"].get(tag, 0) + 1
    
    if chunks:
        stats["avg_text_length"] = total_length / len(chunks)
        stats["min_text_length"] = stats["min_text_length"] if stats["min_text_length"] != float('inf') else 0
    else:
        stats["min_text_length"] = 0
    
    stats["total_pages"] = len(stats["pages"])
    stats["pages"] = sorted(list(stats["pages"]))
    
    return stats

