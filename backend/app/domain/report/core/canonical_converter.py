"""
Raw 보고서 스키마 → Canonical 변환
원본 구조를 보존하며 변환
"""
import uuid
from typing import Dict, Any
from datetime import date, datetime

from app.domain.report.core.schemas import (
    DailyReportSchema,
    WeeklyReportSchema,
    MonthlyReportSchema
)
from app.domain.report.core.canonical_models import (
    CanonicalReport,
    CanonicalDaily,
    CanonicalWeekly,
    CanonicalMonthly,
    DetailTask
)


def parse_date(date_str: str) -> date | None:
    """날짜 문자열을 date 객체로 변환"""
    if not date_str or date_str.strip() == "":
        return None
    
    formats = ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y년 %m월 %d일"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def convert_daily_to_canonical(raw: DailyReportSchema) -> CanonicalReport:
    """
    일일 보고서 Raw → Canonical 변환
    
    Args:
        raw: DailyReportSchema 객체
        
    Returns:
        CanonicalReport 객체
    """
    # 헤더 정보
    header = {
        "작성일자": raw.상단정보.작성일자,
        "성명": raw.상단정보.성명
    }
    
    # 날짜 파싱
    report_date = parse_date(raw.상단정보.작성일자)
    
    # summary_tasks (금일_진행_업무)
    summary_tasks = []
    if raw.금일_진행_업무:
        if isinstance(raw.금일_진행_업무, list):
            summary_tasks = raw.금일_진행_업무
        else:
            summary_tasks = [raw.금일_진행_업무] if raw.금일_진행_업무 else []
    
    # detail_tasks (세부업무)
    detail_tasks = []
    for 세부업무 in raw.세부업무:
        if not 세부업무.업무내용:
            continue
        
        # 시간 추출
        time_start, time_end = None, None
        if " - " in 세부업무.시간:
            parts = 세부업무.시간.split(" - ")
            if len(parts) == 2:
                time_start = parts[0].strip()
                time_end = parts[1].strip()
        elif "~" in 세부업무.시간:
            parts = 세부업무.시간.split("~")
            if len(parts) == 2:
                time_start = parts[0].strip()
                time_end = parts[1].strip()
        
        detail_tasks.append(DetailTask(
            time_start=time_start,
            time_end=time_end,
            text=세부업무.업무내용,
            note=세부업무.비고
        ))
    
    # pending (미종결_업무사항)
    pending = []
    if raw.미종결_업무사항:
        if isinstance(raw.미종결_업무사항, list):
            pending = raw.미종결_업무사항
        else:
            pending = [raw.미종결_업무사항] if raw.미종결_업무사항 else []
    
    # plans (익일_업무계획)
    plans = []
    if raw.익일_업무계획:
        if isinstance(raw.익일_업무계획, list):
            plans = raw.익일_업무계획
        else:
            plans = [raw.익일_업무계획] if raw.익일_업무계획 else []
    
    # notes (특이사항)
    notes = raw.특이사항 or ""
    
    # CanonicalDaily 생성
    canonical_daily = CanonicalDaily(
        header=header,
        summary_tasks=summary_tasks,
        detail_tasks=detail_tasks,
        pending=pending,
        plans=plans,
        notes=notes
    )
    
    # CanonicalReport 생성
    return CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="daily",
        owner=raw.상단정보.성명,
        period_start=report_date,
        period_end=report_date,
        daily=canonical_daily
    )


def convert_weekly_to_canonical(raw: WeeklyReportSchema) -> CanonicalReport:
    """
    주간 보고서 Raw → Canonical 변환
    
    Args:
        raw: WeeklyReportSchema 객체
        
    Returns:
        CanonicalReport 객체
    """
    # 헤더 정보
    header = {
        "작성일자": raw.상단정보.작성일자,
        "성명": raw.상단정보.성명
    }
    
    # 날짜 파싱
    report_date = parse_date(raw.상단정보.작성일자)
    
    # weekly_goals (주간업무목표)
    weekly_goals = []
    for 목표 in raw.주간업무목표:
        if 목표.목표:
            weekly_goals.append(목표.목표)
    
    # weekday_tasks (요일별_세부_업무)
    weekday_tasks = {}
    for 요일, 업무_data in raw.요일별_세부_업무.items():
        tasks = []
        if 업무_data.업무내용:
            tasks.append(업무_data.업무내용)
        if 업무_data.비고:
            tasks.append(f"비고: {업무_data.비고}")
        if tasks:
            weekday_tasks[요일] = tasks
    
    # weekly_highlights (주간_중요_업무)
    weekly_highlights = []
    if raw.주간_중요_업무:
        if isinstance(raw.주간_중요_업무, list):
            weekly_highlights = raw.주간_중요_업무
        else:
            weekly_highlights = [raw.주간_중요_업무] if raw.주간_중요_업무 else []
    
    # notes (특이사항)
    notes = raw.특이사항 or ""
    
    # CanonicalWeekly 생성
    canonical_weekly = CanonicalWeekly(
        header=header,
        weekly_goals=weekly_goals,
        weekday_tasks=weekday_tasks,
        weekly_highlights=weekly_highlights,
        notes=notes
    )
    
    # CanonicalReport 생성
    return CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="weekly",
        owner=raw.상단정보.성명,
        period_start=report_date,
        period_end=report_date,
        weekly=canonical_weekly
    )


def convert_monthly_to_canonical(raw: MonthlyReportSchema) -> CanonicalReport:
    """
    월간 보고서 Raw → Canonical 변환
    
    Args:
        raw: MonthlyReportSchema 객체
        
    Returns:
        CanonicalReport 객체
    """
    # 헤더 정보
    header = {
        "월": raw.상단정보.월,
        "작성일자": raw.상단정보.작성일자,
        "성명": raw.상단정보.성명
    }
    
    # 날짜 파싱
    report_date = parse_date(raw.상단정보.작성일자)
    
    # weekly_summaries (주차별_세부_업무)
    weekly_summaries = {}
    for 주차, 업무_data in raw.주차별_세부_업무.items():
        summaries = []
        if 업무_data.업무내용:
            summaries.append(업무_data.업무내용)
        if 업무_data.비고:
            summaries.append(f"비고: {업무_data.비고}")
        if summaries:
            weekly_summaries[주차] = summaries
    
    # next_month_plan (익월_계획)
    next_month_plan = raw.익월_계획 or ""
    
    # CanonicalMonthly 생성
    canonical_monthly = CanonicalMonthly(
        header=header,
        weekly_summaries=weekly_summaries,
        next_month_plan=next_month_plan
    )
    
    # CanonicalReport 생성
    return CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="monthly",
        owner=raw.상단정보.성명,
        period_start=report_date,
        period_end=report_date,
        monthly=canonical_monthly
    )



