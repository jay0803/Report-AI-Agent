"""
통합 Canonical 청킹 유틸리티

UnifiedCanonical을 RAG용 청크로 변환
기존 report/kpi chunker의 로직을 통합하고 단순화

Author: AI Assistant  
Created: 2025-11-18
"""
import hashlib
from typing import List, Dict, Any

from app.domain.common.canonical_schema import UnifiedCanonical


# ========================================
# 설정
# ========================================
MAX_CHUNK_LENGTH = 1000  # 최대 청크 텍스트 길이 (글자 수)


# ========================================
# ID 생성 함수
# ========================================
def generate_chunk_id(*parts: str) -> str:
    """
    결정적(deterministic) chunk ID 생성
    
    동일한 입력에 대해 항상 동일한 ID를 생성합니다.
    이를 통해 재실행 시 중복 데이터가 쌓이지 않습니다.
    
    Args:
        *parts: ID 생성에 사용할 문자열들
        
    Returns:
        SHA256 해시 기반 ID (32자)
    """
    combined = "|".join(str(p) for p in parts)
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


# ========================================
# 청크 생성 함수
# ========================================
def _create_chunk(chunk_id: str, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """청크 딕셔너리 생성"""
    return {
        "id": chunk_id,
        "text": text,
        "metadata": metadata
    }


def _split_text_by_length(text: str, max_length: int) -> List[str]:
    """
    텍스트를 최대 길이로 분할
    
    문장 단위로 분할을 시도하고, 너무 길면 강제 분할
    """
    if len(text) <= max_length:
        return [text]
    
    # 문장 구분자로 분할 시도
    sentences = text.replace(". ", ".|").replace(".\n", ".|").split("|")
    
    parts = []
    current_part = ""
    
    for sentence in sentences:
        if len(current_part) + len(sentence) <= max_length:
            current_part += sentence
        else:
            if current_part:
                parts.append(current_part)
            # 문장 자체가 너무 길면 강제 분할
            if len(sentence) > max_length:
                for i in range(0, len(sentence), max_length):
                    parts.append(sentence[i:i + max_length])
                current_part = ""
            else:
                current_part = sentence
    
    if current_part:
        parts.append(current_part)
    
    return parts


# ========================================
# Task 청킹
# ========================================
def _chunk_task(
    task: Any,
    unified: UnifiedCanonical,
    task_idx: int
) -> List[Dict[str, Any]]:
    """
    Task를 청크로 변환
    
    Args:
        task: TaskSection 객체
        unified: UnifiedCanonical 객체
        task_idx: Task 인덱스
        
    Returns:
        청크 리스트
    """
    # 텍스트 생성
    text_parts = [f"작업: {task.title}"]
    
    if task.description:
        text_parts.append(f"설명: {task.description}")
    
    if task.time_start and task.time_end:
        text_parts.append(f"시간: {task.time_start} ~ {task.time_end}")
    
    if task.status:
        text_parts.append(f"상태: {task.status}")
    
    if task.note:
        text_parts.append(f"비고: {task.note}")
    
    text = "\n".join(text_parts)
    
    # 메타데이터
    metadata = {
        "chunk_type": "task",
        "doc_id": unified.doc_id,
        "doc_type": unified.doc_type,
        "owner": unified.owner,
        "task_id": task.task_id or f"task_{task_idx}",
        "task_status": task.status
    }
    
    # 날짜 정보
    if unified.single_date:
        metadata["date"] = unified.single_date.isoformat()
    if unified.period_start:
        metadata["period_start"] = unified.period_start.isoformat()
    if unified.period_end:
        metadata["period_end"] = unified.period_end.isoformat()
    
    # 소스 파일
    if "source_file" in unified.metadata:
        metadata["source_file"] = unified.metadata["source_file"]
    
    # 텍스트 길이 체크 및 분할
    if len(text) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(unified.doc_id, "task", str(task_idx), "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(unified.doc_id, "task", str(task_idx), str(idx))
            part_metadata = metadata.copy()
            part_metadata["part"] = idx + 1
            part_metadata["total_parts"] = len(text_parts)
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# KPI 청킹
# ========================================
def _chunk_kpi(
    kpi: Any,
    unified: UnifiedCanonical,
    kpi_idx: int
) -> List[Dict[str, Any]]:
    """
    KPI를 청크로 변환
    
    Args:
        kpi: KPISection 객체
        unified: UnifiedCanonical 객체
        kpi_idx: KPI 인덱스
        
    Returns:
        청크 리스트
    """
    # 텍스트 생성
    text_parts = [f"KPI: {kpi.kpi_name}"]
    
    if kpi.category:
        text_parts.append(f"카테고리: {kpi.category}")
    
    if kpi.value:
        value_text = f"값: {kpi.value}"
        if kpi.unit:
            value_text += f" {kpi.unit}"
        text_parts.append(value_text)
    
    if kpi.delta:
        text_parts.append(f"증감: {kpi.delta}")
    
    if kpi.description:
        text_parts.append(f"설명: {kpi.description}")
    
    if kpi.note:
        text_parts.append(f"비고: {kpi.note}")
    
    text = "\n".join(text_parts)
    
    # 메타데이터
    metadata = {
        "chunk_type": "kpi",
        "doc_id": unified.doc_id,
        "doc_type": unified.doc_type,
        "owner": unified.owner,
        "kpi_name": kpi.kpi_name,
        "kpi_category": kpi.category or ""
    }
    
    # 날짜 정보
    if unified.single_date:
        metadata["date"] = unified.single_date.isoformat()
    if unified.period_start:
        metadata["period_start"] = unified.period_start.isoformat()
    if unified.period_end:
        metadata["period_end"] = unified.period_end.isoformat()
    
    # 소스 파일
    if "source_file" in unified.metadata:
        metadata["source_file"] = unified.metadata["source_file"]
    
    # 페이지 인덱스 (KPI 문서의 경우)
    if "page_index" in unified.metadata:
        metadata["page_index"] = unified.metadata["page_index"]
    
    # 텍스트 길이 체크 및 분할
    if len(text) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(unified.doc_id, "kpi", str(kpi_idx), "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(unified.doc_id, "kpi", str(kpi_idx), str(idx))
            part_metadata = metadata.copy()
            part_metadata["part"] = idx + 1
            part_metadata["total_parts"] = len(text_parts)
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# Issue/Plan 청킹
# ========================================
def _chunk_issue(
    issue: str,
    unified: UnifiedCanonical,
    issue_idx: int
) -> List[Dict[str, Any]]:
    """Issue 청크 생성"""
    metadata = {
        "chunk_type": "issue",
        "doc_id": unified.doc_id,
        "doc_type": unified.doc_type,
        "owner": unified.owner
    }
    
    if unified.single_date:
        metadata["date"] = unified.single_date.isoformat()
    if unified.period_start:
        metadata["period_start"] = unified.period_start.isoformat()
    if unified.period_end:
        metadata["period_end"] = unified.period_end.isoformat()
    
    if "source_file" in unified.metadata:
        metadata["source_file"] = unified.metadata["source_file"]
    
    if len(issue) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(unified.doc_id, "issue", str(issue_idx), "0")
        return [_create_chunk(chunk_id, issue, metadata)]
    else:
        text_parts = _split_text_by_length(issue, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(unified.doc_id, "issue", str(issue_idx), str(idx))
            part_metadata = metadata.copy()
            part_metadata["part"] = idx + 1
            part_metadata["total_parts"] = len(text_parts)
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


def _chunk_plan(
    plan: str,
    unified: UnifiedCanonical,
    plan_idx: int
) -> List[Dict[str, Any]]:
    """Plan 청크 생성"""
    metadata = {
        "chunk_type": "plan",
        "doc_id": unified.doc_id,
        "doc_type": unified.doc_type,
        "owner": unified.owner
    }
    
    if unified.single_date:
        metadata["date"] = unified.single_date.isoformat()
    if unified.period_start:
        metadata["period_start"] = unified.period_start.isoformat()
    if unified.period_end:
        metadata["period_end"] = unified.period_end.isoformat()
    
    if "source_file" in unified.metadata:
        metadata["source_file"] = unified.metadata["source_file"]
    
    if len(plan) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(unified.doc_id, "plan", str(plan_idx), "0")
        return [_create_chunk(chunk_id, plan, metadata)]
    else:
        text_parts = _split_text_by_length(plan, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(unified.doc_id, "plan", str(plan_idx), str(idx))
            part_metadata = metadata.copy()
            part_metadata["part"] = idx + 1
            part_metadata["total_parts"] = len(text_parts)
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# Summary 청킹
# ========================================
def _chunk_summary(unified: UnifiedCanonical) -> List[Dict[str, Any]]:
    """Summary 청크 생성"""
    # 요약 텍스트 생성
    text_parts = [
        f"문서: {unified.title}",
        f"작성자: {unified.owner}" if unified.owner else "",
    ]
    
    if unified.single_date:
        text_parts.append(f"날짜: {unified.single_date.isoformat()}")
    elif unified.period_start and unified.period_end:
        text_parts.append(f"기간: {unified.period_start.isoformat()} ~ {unified.period_end.isoformat()}")
    
    if unified.sections.summary:
        text_parts.append(f"요약: {unified.sections.summary}")
    
    # 통계 추가
    stats = []
    if unified.sections.tasks:
        stats.append(f"작업 {len(unified.sections.tasks)}건")
    if unified.sections.kpis:
        stats.append(f"KPI {len(unified.sections.kpis)}건")
    if unified.sections.issues:
        stats.append(f"이슈 {len(unified.sections.issues)}건")
    if unified.sections.plans:
        stats.append(f"계획 {len(unified.sections.plans)}건")
    
    if stats:
        text_parts.append(", ".join(stats))
    
    text = "\n".join(filter(None, text_parts))
    
    # 메타데이터
    metadata = {
        "chunk_type": "summary",
        "doc_id": unified.doc_id,
        "doc_type": unified.doc_type,
        "owner": unified.owner,
        "task_count": len(unified.sections.tasks),
        "kpi_count": len(unified.sections.kpis),
        "issue_count": len(unified.sections.issues),
        "plan_count": len(unified.sections.plans)
    }
    
    if unified.single_date:
        metadata["date"] = unified.single_date.isoformat()
    if unified.period_start:
        metadata["period_start"] = unified.period_start.isoformat()
    if unified.period_end:
        metadata["period_end"] = unified.period_end.isoformat()
    
    if "source_file" in unified.metadata:
        metadata["source_file"] = unified.metadata["source_file"]
    
    if len(text) <= MAX_CHUNK_LENGTH:
        chunk_id = generate_chunk_id(unified.doc_id, "summary", "0")
        return [_create_chunk(chunk_id, text, metadata)]
    else:
        text_parts = _split_text_by_length(text, MAX_CHUNK_LENGTH)
        chunks = []
        for idx, part in enumerate(text_parts):
            chunk_id = generate_chunk_id(unified.doc_id, "summary", str(idx))
            part_metadata = metadata.copy()
            part_metadata["part"] = idx + 1
            part_metadata["total_parts"] = len(text_parts)
            chunks.append(_create_chunk(chunk_id, part, part_metadata))
        return chunks


# ========================================
# 메인 청킹 함수
# ========================================
def chunk_unified(
    unified: UnifiedCanonical,
    include_summary: bool = True
) -> List[Dict[str, Any]]:
    """
    UnifiedCanonical을 청크로 변환
    
    Args:
        unified: UnifiedCanonical 객체
        include_summary: Summary 청크 포함 여부
        
    Returns:
        청크 리스트
        [
            {
                "id": "chunk_id",
                "text": "chunk_text",
                "metadata": {...}
            },
            ...
        ]
    """
    chunks = []
    
    # (1) Tasks 청킹
    for idx, task in enumerate(unified.sections.tasks):
        task_chunks = _chunk_task(task, unified, idx)
        chunks.extend(task_chunks)
    
    # (2) KPIs 청킹
    for idx, kpi in enumerate(unified.sections.kpis):
        kpi_chunks = _chunk_kpi(kpi, unified, idx)
        chunks.extend(kpi_chunks)
    
    # (3) Issues 청킹
    for idx, issue in enumerate(unified.sections.issues):
        issue_chunks = _chunk_issue(issue, unified, idx)
        chunks.extend(issue_chunks)
    
    # (4) Plans 청킹
    for idx, plan in enumerate(unified.sections.plans):
        plan_chunks = _chunk_plan(plan, unified, idx)
        chunks.extend(plan_chunks)
    
    # (5) Summary 청킹 (옵션)
    if include_summary:
        summary_chunks = _chunk_summary(unified)
        chunks.extend(summary_chunks)
    
    return chunks


# ========================================
# 통계 함수
# ========================================
def get_chunk_statistics(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """청크 통계 정보 반환"""
    if not chunks:
        return {
            "total_chunks": 0,
            "chunk_types": {},
            "avg_text_length": 0,
            "max_text_length": 0,
            "min_text_length": 0
        }
    
    chunk_types = {}
    text_lengths = []
    
    for chunk in chunks:
        chunk_type = chunk["metadata"].get("chunk_type", "unknown")
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        text_lengths.append(len(chunk["text"]))
    
    return {
        "total_chunks": len(chunks),
        "chunk_types": chunk_types,
        "avg_text_length": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
        "max_text_length": max(text_lengths) if text_lengths else 0,
        "min_text_length": min(text_lengths) if text_lengths else 0
    }

