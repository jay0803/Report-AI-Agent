"""
Monthly Report Chain

월간 보고서 자동 생성 체인
target_date가 속한 달의 주간보고서를 조회하여 월간 보고서를 자동 생성
"""
from datetime import date
from calendar import monthrange
from typing import List
from sqlalchemy.orm import Session
import uuid
import re

from app.domain.report.canonical_models import CanonicalReport
# 하위 호환성을 위해 TaskItem, KPIItem은 임시로 유지
try:
    from app.domain.report.schemas import TaskItem, KPIItem
except ImportError:
    from typing import Optional
    from pydantic import BaseModel, Field
    class TaskItem(BaseModel):
        task_id: Optional[str] = None
        title: str = ""
        description: str = ""
        time_start: Optional[str] = None
        time_end: Optional[str] = None
        status: Optional[str] = None
        note: str = ""
    class KPIItem(BaseModel):
        kpi_name: str = ""
        value: str = ""
        unit: Optional[str] = None
        category: Optional[str] = None
        note: str = ""


def get_month_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 달의 1일~말일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (first_day, last_day) 튜플
    """
    first_day = target_date.replace(day=1)
    last_day_num = monthrange(target_date.year, target_date.month)[1]
    last_day = target_date.replace(day=last_day_num)
    return (first_day, last_day)


def calculate_completion_rate(tasks: List[dict]) -> float:
    """
    완료율 계산: 완료된 task / 전체 task
    
    Args:
        tasks: TaskItem dict 리스트
        
    Returns:
        완료율 (0.0 ~ 1.0)
    """
    if not tasks:
        return 0.0
    
    completed = sum(1 for task in tasks if task.get("status") == "완료")
    return completed / len(tasks)




def aggregate_weekly_reports(weekly_reports: List) -> dict:
    """
    여러 주간보고서를 집계하여 월간 보고서 데이터를 생성
    
    Args:
        weekly_reports: 주간보고서 리스트 (WeeklyReport 모델)
        
    Returns:
        집계된 데이터 dict {tasks, plans, issues}
    """
    all_tasks = []
    all_plans = []
    all_issues = []
    
    for weekly_report in weekly_reports:
        report_json = weekly_report.report_json
        
        # tasks 수집
        if "tasks" in report_json:
            for task in report_json["tasks"]:
                # TaskItem 형식으로 변환
                if isinstance(task, dict):
                    task_item = TaskItem(
                        task_id=task.get("task_id"),
                        title=task.get("title", ""),
                        description=task.get("description", ""),
                        time_start=task.get("time_start"),
                        time_end=task.get("time_end"),
                        status=task.get("status", "완료")
                    )
                    all_tasks.append(task_item)
        
        # issues 수집
        if "issues" in report_json:
            all_issues.extend(report_json["issues"])
        
        # plans 수집
        if "plans" in report_json:
            all_plans.extend(report_json["plans"])
    
    return {
        "tasks": all_tasks,
        "plans": all_plans,
        "issues": all_issues
    }


def generate_monthly_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    월간 보고서 자동 생성
    
    주간보고서를 기반으로 월간 보고서를 생성합니다.
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 월의 아무 날짜)
        
    Returns:
        CanonicalReport (monthly)
        
    Raises:
        ValueError: 해당 기간에 주간보고서가 없는 경우
    """
    # 1. 해당 월의 1일~말일 날짜 계산
    first_day, last_day = get_month_range(target_date)
    
    # 2. DB에서 해당 월의 모든 주간보고서 조회
    from app.domain.weekly.repository import WeeklyReportRepository
    
    weekly_reports = WeeklyReportRepository.list_by_owner_and_period_range(
        db=db,
        owner=owner,
        period_start=first_day,
        period_end=last_day
    )
    
    if not weekly_reports:
        raise ValueError(f"해당 기간({first_day}~{last_day})에 주간보고서가 없습니다.")
    
    print(f"[INFO] 주간보고서 {len(weekly_reports)}개 발견: {first_day}~{last_day}")
    
    # 3. 주간보고서 데이터 집계
    aggregated = aggregate_weekly_reports(weekly_reports)
    tasks = aggregated["tasks"]
    issues = aggregated["issues"]
    plans = aggregated["plans"]
    
    print(f"[INFO] 주간보고서 데이터 집계 완료: tasks={len(tasks)}개, issues={len(issues)}개, plans={len(plans)}개")
    
    if not tasks:
        raise ValueError(f"해당 기간({first_day}~{last_day})에 주간보고서에서 업무 데이터를 찾을 수 없습니다.")
    
    # 4. 완료율 계산
    task_dicts = [{"status": task.status} for task in tasks]
    completion_rate = calculate_completion_rate(task_dicts)
    
    # 5. CanonicalReport 생성 (KPI 제거)
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="monthly",
        owner=owner,
        period_start=first_day,
        period_end=last_day,
        tasks=tasks,
        kpis=[],  # KPI 제거
        issues=issues,
        plans=plans,
        metadata={
            "source": "monthly_chain_from_weekly",
            "task_count": len(tasks),
            "issue_count": len(issues),
            "plan_count": len(plans),
            "completion_rate": round(completion_rate, 2),
            "month": f"{target_date.year}-{target_date.month:02d}",
            "weekly_reports_count": len(weekly_reports)
        }
    )
    
    return report

