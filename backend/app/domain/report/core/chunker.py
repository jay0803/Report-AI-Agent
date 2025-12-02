"""
의미 단위 기반 청킹 파이프라인
4개 의미단위 청크로 직접 생성 (summary, detail, pending, plan_note)
"""
import hashlib
from typing import List, Dict, Any
from datetime import date

from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.core.utils_text import (
    extract_customer_names,
    extract_time_range,
    is_pending_related,
    is_summary_related,
    classify_task_category
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
    time_range: str = None
) -> Dict[str, Any]:
    """청크별 메타데이터 생성"""
    customers = extract_customer_names(text)
    task_categories = classify_task_category(text)
    
    metadata = {
        **base_meta,
        "chunk_type": chunk_type,
        "customer": ", ".join(customers) if customers else "",
        "tasks": ", ".join(task_categories) if task_categories else "",
        "is_pending": is_pending_related(text),
        "is_summary_related": is_summary_related(text)
    }
    
    if time_range:
        metadata["time_range"] = time_range
    
    return metadata


def chunk_daily_report(
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    일일 보고서 청킹 (4개 의미단위 청크)
    
    Args:
        canonical: CanonicalReport 객체 (daily 필드 필수)
        
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
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    주간 보고서 청킹 (의미 단위 청크)
    
    Args:
        canonical: CanonicalReport 객체 (weekly 필드 필수)
        
    Returns:
        청크 리스트
    """
    if not canonical.weekly:
        return []
    
    weekly = canonical.weekly
    report_date = canonical.period_start if canonical.period_start else date.today()
    date_str = report_date.isoformat()
    
    # ISO week number 계산
    iso_calendar = report_date.isocalendar()
    week_str = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
    month_str = report_date.strftime("%Y-%m")
    
    # 기간 정보
    period_start_str = canonical.period_start.isoformat() if canonical.period_start else date_str
    period_end_str = canonical.period_end.isoformat() if canonical.period_end else date_str
    
    chunks = []
    base_meta = _build_base_metadata(canonical)
    
    # 1. header_chunk
    header_text = f"작성일자: {weekly.header.get('작성일자', '')}\n작성자: {weekly.header.get('성명', '')}"
    if header_text.strip():
        header_metadata = _build_metadata_for_chunk("header_chunk", header_text, base_meta)
        # 상세 메타데이터 추가
        header_metadata.update({
            "date": date_str,
            "level": "weekly",
            "week": week_str,
            "month": month_str,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "doc_id": f"weekly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "header", "0"),
            "text": header_text,
            "metadata": header_metadata
        })
    
    # 2. weekly_goal_chunk (각 목표를 개별 청크로)
    for idx, goal in enumerate(weekly.weekly_goals):
        if not goal.strip():
            continue
        
        goal_metadata = _build_metadata_for_chunk("weekly_goal_chunk", goal, base_meta)
        goal_metadata.update({
            "date": date_str,
            "level": "weekly",
            "chunk_type": "weekly_goal",
            "week": week_str,
            "month": month_str,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "goal_index": idx,
            "doc_id": f"weekly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "weekly_goal", str(idx)),
            "text": goal,
            "metadata": goal_metadata
        })
    
    # 3. weekday_task_chunk (요일별 업무)
    for 요일, tasks in weekly.weekday_tasks.items():
        for idx, task in enumerate(tasks):
            if not task.strip():
                continue
            
            task_text = f"[{요일}] {task}"
            task_metadata = _build_metadata_for_chunk("weekday_task_chunk", task_text, base_meta)
            task_metadata.update({
                "date": date_str,
                "level": "weekly",
                "chunk_type": "weekday_task",
                "week": week_str,
                "month": month_str,
                "period_start": period_start_str,
                "period_end": period_end_str,
                "weekday": 요일,
                "task_index": idx,
                "doc_id": f"weekly_{date_str.replace('-', '_')}"
            })
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "weekday_task", f"{요일}_{idx}"),
                "text": task_text,
                "metadata": task_metadata
            })
    
    # 4. weekly_highlight_chunk
    for idx, highlight in enumerate(weekly.weekly_highlights):
        if not highlight.strip():
            continue
        
        highlight_metadata = _build_metadata_for_chunk("weekly_highlight_chunk", highlight, base_meta)
        highlight_metadata.update({
            "date": date_str,
            "level": "weekly",
            "chunk_type": "weekly_highlight",
            "week": week_str,
            "month": month_str,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "highlight_index": idx,
            "doc_id": f"weekly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "weekly_highlight", str(idx)),
            "text": highlight,
            "metadata": highlight_metadata
        })
    
    # 5. note_chunk
    if weekly.notes and weekly.notes.strip():
        note_metadata = _build_metadata_for_chunk("note_chunk", weekly.notes, base_meta)
        note_metadata.update({
            "date": date_str,
            "level": "weekly",
            "chunk_type": "note",
            "week": week_str,
            "month": month_str,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "doc_id": f"weekly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "note", "0"),
            "text": weekly.notes,
            "metadata": note_metadata
        })
    
    return chunks


def chunk_monthly_report(
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    월간 보고서 청킹 (의미 단위 청크)
    
    Args:
        canonical: CanonicalReport 객체 (monthly 필드 필수)
        
    Returns:
        청크 리스트
    """
    if not canonical.monthly:
        return []
    
    monthly = canonical.monthly
    report_date = canonical.period_start if canonical.period_start else date.today()
    date_str = report_date.isoformat()
    
    # ISO week number 계산
    iso_calendar = report_date.isocalendar()
    week_str = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
    month_str = report_date.strftime("%Y-%m")
    
    # 기간 정보
    period_start_str = canonical.period_start.isoformat() if canonical.period_start else date_str
    period_end_str = canonical.period_end.isoformat() if canonical.period_end else date_str
    
    # 월 정보 추출 (헤더에서)
    month_from_header = monthly.header.get('월', '')
    
    chunks = []
    base_meta = _build_base_metadata(canonical)
    
    # header_chunk
    header_text = f"월: {monthly.header.get('월', '')}\n작성일자: {monthly.header.get('작성일자', '')}\n작성자: {monthly.header.get('성명', '')}"
    if header_text.strip():
        header_metadata = _build_metadata_for_chunk("header_chunk", header_text, base_meta)
        header_metadata.update({
            "date": date_str,
            "level": "monthly",
            "week": week_str,
            "month": month_str,
            "month_name": month_from_header,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "doc_id": f"monthly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "header", "0"),
            "text": header_text,
            "metadata": header_metadata
        })
    
    # weekly_summary_chunk
    for 주차, summaries in monthly.weekly_summaries.items():
        for idx, summary in enumerate(summaries):
            if not summary.strip():
                continue
            
            summary_text = f"[{주차}] {summary}"
            summary_metadata = _build_metadata_for_chunk("weekly_summary_chunk", summary_text, base_meta)
            summary_metadata.update({
                "date": date_str,
                "level": "monthly",
                "chunk_type": "weekly_summary",
                "week": week_str,
                "month": month_str,
                "month_name": month_from_header,
                "period_start": period_start_str,
                "period_end": period_end_str,
                "week_of_month": 주차,
                "summary_index": idx,
                "doc_id": f"monthly_{date_str.replace('-', '_')}"
            })
            chunks.append({
                "id": generate_chunk_id(canonical.report_id, "weekly_summary", f"{주차}_{idx}"),
                "text": summary_text,
                "metadata": summary_metadata
            })
    
    # next_month_plan_chunk
    if monthly.next_month_plan and monthly.next_month_plan.strip():
        plan_metadata = _build_metadata_for_chunk("next_month_plan_chunk", monthly.next_month_plan, base_meta)
        plan_metadata.update({
            "date": date_str,
            "level": "monthly",
            "chunk_type": "next_month_plan",
            "week": week_str,
            "month": month_str,
            "month_name": month_from_header,
            "period_start": period_start_str,
            "period_end": period_end_str,
            "doc_id": f"monthly_{date_str.replace('-', '_')}"
        })
        chunks.append({
            "id": generate_chunk_id(canonical.report_id, "next_month_plan", "0"),
            "text": monthly.next_month_plan,
            "metadata": plan_metadata
        })
    
    return chunks


def chunk_canonical_report(
    canonical: CanonicalReport
) -> List[Dict[str, Any]]:
    """
    CanonicalReport를 타입에 따라 청킹 (의미 단위 청킹만 사용)
    
    Args:
        canonical: CanonicalReport 객체
        
    Returns:
        청크 리스트
    """
    if canonical.report_type == "daily":
        return chunk_daily_report(canonical)
    elif canonical.report_type == "weekly":
        return chunk_weekly_report(canonical)
    elif canonical.report_type == "monthly":
        return chunk_monthly_report(canonical)
    else:
        return []

