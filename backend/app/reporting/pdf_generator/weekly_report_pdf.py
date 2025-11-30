"""
Weekly Report PDF Generator

주간보고서를 PDF로 생성
템플릿: backend/Data/reports/주간 업무 보고서.pdf
"""
from datetime import date
from typing import Optional
from pathlib import Path

from app.reporting.pdf_generator.base import BasePDFGenerator
from app.reporting.pdf_generator.utils import format_korean_date, truncate_text
from app.domain.report.schemas import CanonicalReport


class WeeklyReportPDFGenerator(BasePDFGenerator):
    """주간보고서 PDF 생성기"""
    
    def __init__(self):
        super().__init__("주간 업무 보고서.pdf")
    
    def generate(
        self, 
        report: CanonicalReport,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        주간보고서 PDF 생성
        
        Args:
            report: CanonicalReport 객체 (weekly 타입)
            output_filename: 출력 파일명
            
        Returns:
            PDF 바이트 스트림
        """
        self._init_canvas()
        
        # ========================================
        # 헤더: 작성일자(금요일), 성명
        # 기간(월~금)은 데이터 저장용으로만 사용, PDF에는 출력하지 않음
        # ========================================
        작성일자 = format_korean_date(report.period_end)  # 금요일 날짜
        성명 = report.owner
        
        self.draw_text(175, self._to_pdf_y(107), 작성일자, font_size=11)  # TODO: 좌표 조정
        self.draw_text(340, self._to_pdf_y(107), 성명, font_size=11)  # TODO: 좌표 조정
        
        # ========================================
        # 주간 업무 목표 (최대 3개)
        # metadata의 weekly_goals 우선, 없으면 plans 사용
        # ========================================
        주간_목표 = report.metadata.get('weekly_goals', [])
        
        # metadata에 없으면 plans 사용 (fallback)
        if not 주간_목표 and report.plans:
            주간_목표 = report.plans[:3]  # 최대 3개
        
        if 주간_목표:
            y_offset = 213  # TODO: 좌표 조정
            for idx, goal in enumerate(주간_목표[:3]):  # 최대 3개
                goal_text = goal if isinstance(goal, str) else goal.get('title', str(goal))
                plan_text = f"{truncate_text(goal_text, 50)}"
                self.draw_text(
                    x=180,  # TODO: 좌표 조정
                    y=self._to_pdf_y(y_offset + (idx * 30)),
                    text=plan_text,
                    font_size=10
                )
        
        # ========================================
        # 요일별 세부 업무 (월~금)
        # LLM이 생성한 요약 결과만 사용 (원본 task 사용 안 함)
        # ========================================
        weekdays = ['월요일', '화요일', '수요일', '목요일', '금요일']
        
        # metadata에서 LLM 요약 결과 가져오기
        daily_tasks_by_day = report.metadata.get('daily_tasks_by_day', {})
        
        table_start_y = 391  # TODO: 좌표 조정
        row_height = 49  # TODO: 요일별 행 높이 조정
        
        for day_idx, weekday in enumerate(weekdays):
            current_y = self._to_pdf_y(table_start_y + (day_idx * row_height))
            
            # 해당 요일의 LLM 요약 결과만 사용
            # 원본 task는 절대 사용하지 않음
            day_summary_tasks = daily_tasks_by_day.get(weekday, [])
            
            # 요약 데이터가 있으면 출력, 없으면 비워둠 (fallback 없음)
            if day_summary_tasks:
                # LLM 요약 결과를 그대로 출력 (최대 3개)
                task_texts = [f"• {truncate_text(task, 50)}" for task in day_summary_tasks[:3]]
                task_summary = "\n".join(task_texts)
                
                self.draw_multiline_text(
                    x=200,  # TODO: 좌표 조정
                    y=current_y,
                    text=task_summary,
                    font_size=9,
                    line_height=12
                )
            # else: 요약 데이터가 없으면 해당 요일은 비워둠 (아무것도 출력하지 않음)
        
        # ========================================
        # 주간 중요 업무 (metadata에서 추출)
        # 요일별 세부 업무에서 우선순위 높은 항목 3개
        # ========================================
        중요_업무_리스트 = report.metadata.get('important_tasks', [])
        if 중요_업무_리스트:
            중요_업무_텍스트 = "\n".join([f"• {task}" for task in 중요_업무_리스트[:3]])
            self.draw_multiline_text(
                x=130,  # TODO: 좌표 조정
                y=self._to_pdf_y(660),
                text=중요_업무_텍스트,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 특이사항 / 이슈
        # ========================================
        if report.issues:
            이슈_텍스트 = "\n".join([f"• {issue}" for issue in report.issues[:3]])
            self.draw_multiline_text(
                x=130,  # TODO: 좌표 조정
                y=self._to_pdf_y(745),
                text=이슈_텍스트,
                font_size=10,
                line_height=14
            )
        
        self.save_overlay()
        
        if output_filename is None:
            output_filename = f"주간보고서_{report.owner}_{format_korean_date(report.period_start)}.pdf"
        
        # 주간 보고서 전용 디렉토리에 저장
        weekly_dir = self.OUTPUT_DIR / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)
        output_path = weekly_dir / output_filename
        pdf_bytes = self.merge_with_template(output_path)
        
        return pdf_bytes


def generate_weekly_pdf_from_json(report_json: dict, output_filename: Optional[str] = None) -> bytes:
    """JSON에서 직접 PDF 생성"""
    report = CanonicalReport(**report_json)
    generator = WeeklyReportPDFGenerator()
    return generator.generate(report, output_filename)

