"""
새로운 청킹 파이프라인
의미 단위 기반 직접 생성 + 선택적 CharacterTextSplitter
"""
import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import date

from langchain.text_splitter import CharacterTextSplitter
from openai import OpenAI

from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.core.utils_text import (
    extract_customer_names,
    extract_time_range,
    is_pending_related,
    is_summary_related,
    classify_task_category
)


# CharacterTextSplitter 설정 (2차 보조 청킹용)
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50
_text_splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len
)


def generate_chunk_id(*parts: str) -> str:
    """청크 ID 생성"""
    combined = "|".join(str(p) for p in parts)
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]


def _build_base_metadata(canonical: CanonicalReport) -> Dict[str, Any]:
    """공통 메타데이터 생성"""
    report_date = canonical.period_start if canonical.period_start else date.today()
    
    return {
        "report_id": canonical.report_id,
        "report_type": canonical.report_type,
        "date": report_date.isoformat(),
        "week_id": f"{report_date.isocalendar()[0]}-W{report_date.isocalendar()[1]:02d}",
        "month_id": report_date.strftime("%Y-%m"),
        "owner": canonical.owner,
        "doc_id": f"{canonical.report_type}_{report_date.strftime('%Y_%m_%d')}"
    }


def _build_metadata_for_chunk(
    chunk_type: str,
    text: str,
    base_meta: Dict[str, Any],
    chunk_index: int,
    time_range: Optional[str] = None
) -> Dict[str, Any]:
    """청크별 메타데이터 생성"""
    customers = extract_customer_names(text)
    task_categories = classify_task_category(text)
    
    metadata = {
        **base_meta,
        "chunk_type": chunk_type,
        "chunk_index": chunk_index,
        "customer": ", ".join(customers) if customers else "",
        "tasks": ", ".join(task_categories) if task_categories else "",
        "is_pending": is_pending_related(text),
        "is_summary_related": is_summary_related(text)
    }
    
    if time_range:
        metadata["time_range"] = time_range
    
    return metadata


def _apply_secondary_split(text: str, base_meta: Dict[str, Any], chunk_index: int, chunk_type: str) -> List[Dict[str, Any]]:
    """
    2차 보조 청킹 (300자 이상일 때만)
    
    Args:
        text: 분할할 텍스트
        base_meta: 공통 메타데이터
        chunk_index: 시작 청크 인덱스
        chunk_type: 청크 타입
        
    Returns:
        분할된 청크 리스트
    """
    if len(text) < CHUNK_SIZE:
        return []
    
    split_texts = _text_splitter.split_text(text)
    chunks = []
    
    for idx, split_text in enumerate(split_texts):
        if not split_text.strip():
            continue
        
        time_range = extract_time_range(split_text) if chunk_type == "detail_task_chunk" else None
        metadata = _build_metadata_for_chunk(
            chunk_type=chunk_type,
            text=split_text,
            base_meta=base_meta,
            chunk_index=chunk_index + idx,
            time_range=time_range
        )
        
        chunks.append({
            "id": generate_chunk_id(base_meta["report_id"], "split", str(chunk_index + idx)),
            "text": split_text,
            "metadata": metadata
        })
    
    return chunks


def _apply_llm_refine(chunk: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    LLM 재정제 (청킹 이후에만 수행)
    
    Args:
        chunk: 청크 딕셔너리
        api_key: OpenAI API 키
        
    Returns:
        재정제된 청크 (원문 text는 유지, refined_text는 metadata에 저장)
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return chunk
    
    client = OpenAI(api_key=api_key)
    
    try:
        prompt = f"""다음 텍스트를 의미 단위의 문장 묶음으로 재정렬하세요.
불필요한 부분은 제거하고, 핵심 의미만 유지하세요.

원본:
{chunk["text"]}

재정렬된 텍스트:"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        refined_text = response.choices[0].message.content.strip()
        if refined_text:
            chunk["metadata"]["refined_text"] = refined_text
    except Exception:
        # 재정제 실패 시 원문 유지
        pass
    
    return chunk


def chunk_daily_report(
    canonical: CanonicalReport,
    api_key: Optional[str] = None,
    use_llm_refine: bool = True
) -> List[Dict[str, Any]]:
    """
    일일 보고서 청킹 (4개 의미단위 청크로 통합)
    
    Args:
        canonical: CanonicalReport 객체 (daily 필드 필수)
        api_key: OpenAI API 키 (사용하지 않음, 호환성 유지)
        use_llm_refine: LLM 재정제 사용 여부 (사용하지 않음, 호환성 유지)
        
    Returns:
        4개 청크 리스트 (summary, detail, pending, plan_note)
    """
    if not canonical.daily:
        return []
    
    daily = canonical.daily
    report_date = canonical.period_start if canonical.period_start else date.today()
    date_str = report_date.isoformat()
    
    # ISO week number 계산
    iso_calendar = report_date.isocalendar()
    week_str = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
    month_str = report_date.strftime("%Y-%m")
    
    chunks = []
    
    # ========================================
    # 1. SUMMARY 청크
    # ========================================
    if daily.summary_tasks:
        summary_text = "\n".join([f"{idx+1}. {task}" for idx, task in enumerate(daily.summary_tasks)])
        summary_doc = f"[일일_SUMMARY] {date_str}\n{summary_text}"
        
        metadata_summary = {
            "date": date_str,
            "level": "daily",
            "chunk_type": "summary",
            "week": week_str,
            "month": month_str,
            "owner": canonical.owner,
            "report_id": canonical.report_id,
            "report_type": "daily",
            "doc_id": f"daily_{date_str.replace('-', '_')}"
        }
        
        chunks.append({
            "id": f"{date_str}_summary",
            "text": summary_doc,
            "metadata": metadata_summary
        })
    
    # ========================================
    # 2. DETAIL 청크
    # ========================================
    if daily.detail_tasks:
        detail_lines = []
        start_time = None
        end_time = None
        
        for task in daily.detail_tasks:
            if task.time_start:
                if start_time is None:
                    start_time = task.time_start
                end_time = task.time_end or task.time_start
            
            task_line = task.text
            if task.note:
                task_line += f" (비고: {task.note})"
            if task.time_start and task.time_end:
                task_line = f"[{task.time_start}-{task.time_end}] {task_line}"
            elif task.time_start:
                task_line = f"[{task.time_start}] {task_line}"
            
            detail_lines.append(task_line)
        
        detail_text = "\n".join(detail_lines)
        detail_doc = f"[일일_DETAIL] {date_str}\n{detail_text}"
        
        metadata_detail = {
            "date": date_str,
            "level": "daily",
            "chunk_type": "detail",
            "week": week_str,
            "month": month_str,
            "owner": canonical.owner,
            "report_id": canonical.report_id,
            "report_type": "daily",
            "doc_id": f"daily_{date_str.replace('-', '_')}"
        }
        
        if start_time:
            metadata_detail["시작시간"] = start_time
        if end_time:
            metadata_detail["끝시간"] = end_time
        
        chunks.append({
            "id": f"{date_str}_detail",
            "text": detail_doc,
            "metadata": metadata_detail
        })
    
    # ========================================
    # 3. PENDING 청크
    # ========================================
    if daily.pending:
        pending_text = "\n".join([f"• {item}" for item in daily.pending])
        pending_doc = f"[일일_PENDING] {date_str}\n{pending_text}"
        
        metadata_pending = {
            "date": date_str,
            "level": "daily",
            "chunk_type": "pending",
            "week": week_str,
            "month": month_str,
            "owner": canonical.owner,
            "report_id": canonical.report_id,
            "report_type": "daily",
            "doc_id": f"daily_{date_str.replace('-', '_')}"
        }
        
        chunks.append({
            "id": f"{date_str}_pending",
            "text": pending_doc,
            "metadata": metadata_pending
        })
    
    # ========================================
    # 4. PLAN_NOTE 청크
    # ========================================
    plan_note_parts = []
    
    if daily.plans:
        plan_text = "\n".join([f"• {plan}" for plan in daily.plans])
        plan_note_parts.append(f"익일 계획:\n{plan_text}")
    
    if daily.notes and daily.notes.strip():
        plan_note_parts.append(f"특이사항:\n{daily.notes}")
    
    if plan_note_parts:
        plan_note_text = "\n\n".join(plan_note_parts)
        plan_note_doc = f"[일일_PLAN_NOTE] {date_str}\n{plan_note_text}"
        
        metadata_plan = {
            "date": date_str,
            "level": "daily",
            "chunk_type": "plan_note",
            "week": week_str,
            "month": month_str,
            "owner": canonical.owner,
            "report_id": canonical.report_id,
            "report_type": "daily",
            "doc_id": f"daily_{date_str.replace('-', '_')}"
        }
        
        chunks.append({
            "id": f"{date_str}_plan_note",
            "text": plan_note_doc,
            "metadata": metadata_plan
        })
    
    return chunks


def chunk_weekly_report(
    canonical: CanonicalReport,
    api_key: Optional[str] = None,
    use_llm_refine: bool = True
) -> List[Dict[str, Any]]:
    """
    주간 보고서 청킹 (의미 단위 직접 생성)
    
    Args:
        canonical: CanonicalReport 객체 (weekly 필드 필수)
        api_key: OpenAI API 키
        use_llm_refine: LLM 재정제 사용 여부
        
    Returns:
        청크 리스트
    """
    if not canonical.weekly:
        return []
    
    base_meta = _build_base_metadata(canonical)
    chunks = []
    chunk_index = 0
    
    weekly = canonical.weekly
    
    # 1. header_chunk
    header_text = f"작성일자: {weekly.header.get('작성일자', '')}\n작성자: {weekly.header.get('성명', '')}"
    if header_text.strip():
        metadata = _build_metadata_for_chunk("header_chunk", header_text, base_meta, chunk_index)
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "header", "0"),
            "text": header_text,
            "metadata": metadata
        })
        chunk_index += 1
    
    # 2. weekly_goal_chunk (각 목표를 개별 청크로)
    for idx, goal in enumerate(weekly.weekly_goals):
        if not goal.strip():
            continue
        
        if len(goal) >= CHUNK_SIZE:
            split_chunks = _apply_secondary_split(goal, base_meta, chunk_index, "weekly_goal_chunk")
            if split_chunks:
                chunks.extend(split_chunks)
                chunk_index += len(split_chunks)
                continue
        
        metadata = _build_metadata_for_chunk("weekly_goal_chunk", goal, base_meta, chunk_index)
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "weekly_goal", str(idx)),
            "text": goal,
            "metadata": metadata
        })
        chunk_index += 1
    
    # 3. weekday_task_chunk (요일별 업무)
    for 요일, tasks in weekly.weekday_tasks.items():
        for idx, task in enumerate(tasks):
            if not task.strip():
                continue
            
            task_text = f"[{요일}] {task}"
            
            if len(task_text) >= CHUNK_SIZE:
                split_chunks = _apply_secondary_split(task_text, base_meta, chunk_index, "weekday_task_chunk")
                if split_chunks:
                    chunks.extend(split_chunks)
                    chunk_index += len(split_chunks)
                    continue
            
            metadata = _build_metadata_for_chunk("weekday_task_chunk", task_text, base_meta, chunk_index)
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "weekday_task", f"{요일}_{idx}"),
                "text": task_text,
                "metadata": metadata
            })
            chunk_index += 1
    
    # 4. weekly_highlight_chunk
    for idx, highlight in enumerate(weekly.weekly_highlights):
        if not highlight.strip():
            continue
        
        if len(highlight) >= CHUNK_SIZE:
            split_chunks = _apply_secondary_split(highlight, base_meta, chunk_index, "weekly_highlight_chunk")
            if split_chunks:
                chunks.extend(split_chunks)
                chunk_index += len(split_chunks)
                continue
        
        metadata = _build_metadata_for_chunk("weekly_highlight_chunk", highlight, base_meta, chunk_index)
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "weekly_highlight", str(idx)),
            "text": highlight,
            "metadata": metadata
        })
        chunk_index += 1
    
    # 5. note_chunk
    if weekly.notes and weekly.notes.strip():
        if len(weekly.notes) >= CHUNK_SIZE:
            split_chunks = _apply_secondary_split(weekly.notes, base_meta, chunk_index, "note_chunk")
            if split_chunks:
                chunks.extend(split_chunks)
                chunk_index += len(split_chunks)
        else:
            metadata = _build_metadata_for_chunk("note_chunk", weekly.notes, base_meta, chunk_index)
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "note", "0"),
                "text": weekly.notes,
                "metadata": metadata
            })
            chunk_index += 1
    
    # LLM 재정제
    if use_llm_refine:
        for chunk in chunks:
            if chunk["metadata"]["chunk_type"] != "header_chunk":
                chunk = _apply_llm_refine(chunk, api_key)
    
    return chunks


def chunk_monthly_report(
    canonical: CanonicalReport,
    api_key: Optional[str] = None,
    use_llm_refine: bool = True
) -> List[Dict[str, Any]]:
    """
    월간 보고서 청킹
    """
    if not canonical.monthly:
        return []
    
    base_meta = _build_base_metadata(canonical)
    chunks = []
    chunk_index = 0
    
    monthly = canonical.monthly
    
    # header_chunk
    header_text = f"월: {monthly.header.get('월', '')}\n작성일자: {monthly.header.get('작성일자', '')}\n작성자: {monthly.header.get('성명', '')}"
    if header_text.strip():
        metadata = _build_metadata_for_chunk("header_chunk", header_text, base_meta, chunk_index)
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "header", "0"),
            "text": header_text,
            "metadata": metadata
        })
        chunk_index += 1
    
    # weekly_summary_chunk
    for 주차, summaries in monthly.weekly_summaries.items():
        for idx, summary in enumerate(summaries):
            if not summary.strip():
                continue
            
            summary_text = f"[{주차}] {summary}"
            
            if len(summary_text) >= CHUNK_SIZE:
                split_chunks = _apply_secondary_split(summary_text, base_meta, chunk_index, "weekly_summary_chunk")
                if split_chunks:
                    chunks.extend(split_chunks)
                    chunk_index += len(split_chunks)
                    continue
            
            metadata = _build_metadata_for_chunk("weekly_summary_chunk", summary_text, base_meta, chunk_index)
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "weekly_summary", f"{주차}_{idx}"),
                "text": summary_text,
                "metadata": metadata
            })
            chunk_index += 1
    
    # next_month_plan_chunk
    if monthly.next_month_plan and monthly.next_month_plan.strip():
        if len(monthly.next_month_plan) >= CHUNK_SIZE:
            split_chunks = _apply_secondary_split(monthly.next_month_plan, base_meta, chunk_index, "next_month_plan_chunk")
            if split_chunks:
                chunks.extend(split_chunks)
                chunk_index += len(split_chunks)
        else:
            metadata = _build_metadata_for_chunk("next_month_plan_chunk", monthly.next_month_plan, base_meta, chunk_index)
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "next_month_plan", "0"),
                "text": monthly.next_month_plan,
                "metadata": metadata
            })
            chunk_index += 1
    
    # LLM 재정제
    if use_llm_refine:
        for chunk in chunks:
            if chunk["metadata"]["chunk_type"] != "header_chunk":
                chunk = _apply_llm_refine(chunk, api_key)
    
    return chunks


def chunk_canonical_report(
    canonical: CanonicalReport,
    api_key: Optional[str] = None,
    use_llm_refine: bool = True
) -> List[Dict[str, Any]]:
    """
    CanonicalReport를 타입에 따라 청킹
    
    Args:
        canonical: CanonicalReport 객체
        api_key: OpenAI API 키
        use_llm_refine: LLM 재정제 사용 여부
        
    Returns:
        청크 리스트
    """
    if canonical.report_type == "daily":
        return chunk_daily_report(canonical, api_key, use_llm_refine)
    elif canonical.report_type == "weekly":
        return chunk_weekly_report(canonical, api_key, use_llm_refine)
    elif canonical.report_type == "monthly":
        return chunk_monthly_report(canonical, api_key, use_llm_refine)
    else:
        return []

