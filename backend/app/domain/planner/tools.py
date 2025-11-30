"""
Report Retrieval Tool

전날 보고서에서 미종결 업무와 익일 계획을 추출합니다.

Author: AI Assistant
Created: 2025-11-18
Updated: 2025-11-19 (PostgreSQL 직접 조회로 변경)
"""
from typing import Dict, List, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.domain.daily.repository import DailyReportRepository
from app.domain.report.schemas import CanonicalReport


class YesterdayReportTool:
    """전날 보고서 검색 도구 (PostgreSQL 직접 조회)"""
    
    def __init__(self, db: Session):
        """
        초기화
        
        Args:
            db: SQLAlchemy 세션
        """
        self.db = db
    
    def get_yesterday_report(
        self,
        owner: str,
        target_date: date
    ) -> Dict[str, Any]:
        """
        전날 보고서에서 미종결 업무와 익일 계획 추출 (PostgreSQL에서 직접 조회)
        
        Args:
            owner: 작성자명
            target_date: 기준 날짜 (오늘)
            
        Returns:
            {
                "unresolved": List[str],  # 미종결 업무 (issues)
                "next_day_plan": List[str],  # 익일 계획 (plans)
                "tasks": List[str],  # 업무 목록
                "raw_chunks": List[dict],  # 원본 데이터
                "found": bool  # 데이터 발견 여부
            }
        """
        # 전날 날짜 계산
        yesterday = target_date - timedelta(days=1)
        yesterday_str = yesterday.isoformat()
        
        print(f"[DEBUG] YesterdayReportTool: owner={owner}, target_date={target_date}, yesterday={yesterday}")
        
        # PostgreSQL에서 전날 보고서 직접 조회
        daily_report = DailyReportRepository.get_by_owner_and_date(
            self.db,
            owner,
            yesterday
        )
        
        if not daily_report:
            # 🔥 전날 데이터가 없으면 최근 데이터 찾기 (최대 7일 전까지)
            print(f"[DEBUG] 전날({yesterday}) 데이터 없음. 최근 데이터 검색 중...")
            recent_reports = DailyReportRepository.list_by_owner(
                self.db,
                owner,
                skip=0,
                limit=10
            )
            
            # 최근 보고서 중 가장 가까운 날짜 찾기
            closest_report = None
            closest_date = None
            for report in recent_reports:
                if report.date < target_date:  # 오늘 이전 데이터만
                    if closest_date is None or report.date > closest_date:
                        closest_date = report.date
                        closest_report = report
            
            if closest_report:
                print(f"[DEBUG] 최근 데이터 발견: {closest_date} (전날 대신 사용)")
                daily_report = closest_report
                yesterday = closest_date
                yesterday_str = yesterday.isoformat()
            else:
                # 최근 데이터도 없음
                print(f"[DEBUG] 최근 데이터도 없음. owner={owner}의 모든 보고서 개수 확인 중...")
                total_count = DailyReportRepository.count_by_owner(self.db, owner)
                print(f"[DEBUG] {owner}의 전체 보고서 개수: {total_count}개")
                
                return {
                    "unresolved": [],
                    "next_day_plan": [],
                    "tasks": [],
                    "raw_chunks": [],
                    "found": False,
                    "search_date": yesterday_str,
                    "owner": owner
                }
        
        # CanonicalReport로 변환
        report_json = daily_report.report_json
        report = CanonicalReport(**report_json)
        
        # 미종결 업무 추출
        unresolved = report.issues or []
        
        # 익일 계획 추출 (metadata에서)
        next_day_plan = []
        if report.metadata and "next_plan" in report.metadata:
            next_plan = report.metadata["next_plan"]
            if isinstance(next_plan, str):
                # 문자열이면 줄바꿈으로 분리
                next_day_plan = [line.strip() for line in next_plan.split('\n') if line.strip()]
            elif isinstance(next_plan, list):
                next_day_plan = next_plan
        
        # 업무 목록 추출 (요약용)
        tasks = []
        for task in report.tasks or []:
            task_text = task.title or task.description or ""
            if task_text:
                tasks.append(task_text)
        
        # 원본 데이터
        raw_chunks = [{
            "chunk_id": f"daily_{daily_report.id}",
            "chunk_type": "daily_report",
            "text": f"일일보고서: {yesterday_str}",
            "metadata": {
                "owner": owner,
                "date": yesterday_str,
                "report_id": str(daily_report.id)
            }
        }]
        
        return {
            "unresolved": unresolved,
            "next_day_plan": next_day_plan,
            "tasks": tasks,
            "raw_chunks": raw_chunks,
            "found": True,
            "search_date": yesterday_str,
            "owner": owner
        }


def get_yesterday_report(
    owner: str,
    target_date: date,
    db: Session
) -> Dict[str, Any]:
    """
    헬퍼 함수: 전날 보고서 가져오기 (PostgreSQL 직접 조회)
    
    Args:
        owner: 작성자명
        target_date: 기준 날짜
        db: SQLAlchemy 세션
        
    Returns:
        전날 보고서 정보 딕셔너리
    """
    tool = YesterdayReportTool(db)
    return tool.get_yesterday_report(owner, target_date)

