"""
Monthly Report PDF Generator

월간보고서를 PDF로 생성
템플릿: backend/Data/reports/월간 업무 보고서.pdf
"""
from datetime import date
from typing import Optional
from pathlib import Path

from app.reporting.pdf_generator.base import BasePDFGenerator
from app.reporting.pdf_generator.utils import format_korean_date, truncate_text
from app.domain.report.schemas import CanonicalReport


class MonthlyReportPDFGenerator(BasePDFGenerator):
    """월간보고서 PDF 생성기"""
    
    def __init__(self):
        super().__init__("월간 업무 보고서.pdf")
    
    def generate(
        self, 
        report: CanonicalReport,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        월간보고서 PDF 생성
        
        Args:
            report: CanonicalReport 객체 (monthly 타입)
            output_filename: 출력 파일명
            
        Returns:
            PDF 바이트 스트림
        """
        self._init_canvas()
        
        # ========================================
        # 헤더: 월, 작성일자, 성명
        # ========================================
        월 = f"{report.period_start.month}"
        작성일자 = format_korean_date(report.period_end)
        성명 = report.owner
        
        self.draw_text(50, self._to_pdf_y(106), 월, font_size=13)  # TODO: 좌표 조정
        self.draw_text(170, self._to_pdf_y(106), 작성일자, font_size=11)  # TODO: 좌표 조정
        self.draw_text(340, self._to_pdf_y(106), 성명, font_size=11)  # TODO: 좌표 조정
        
        # ========================================
        # 월간 핵심 지표 (KPIs)
        # ========================================
        kpi_start_y = 180  # TODO: 좌표 조정
        
        if report.kpis:
            for idx, kpi in enumerate(report.kpis[:5]):  # 최대 5개
                kpi_text = f"{kpi.kpi_name}: {kpi.value} {kpi.unit or ''}"
                self.draw_text(
                    x=170,  # TODO: 좌표 조정
                    y=self._to_pdf_y(kpi_start_y + (idx * 30)),
                    text=kpi_text,
                    font_size=10
                )
        
        # ========================================
        # 주차별 세부 업무 (1주차 ~ 4/5주차)
        # ========================================
        weeks = ['1주차', '2주차', '3주차', '4주차', '5주차']
        tasks_per_week = len(report.tasks) // 4 if len(report.tasks) >= 4 else 1
        table_start_y = 391  # TODO: 좌표 조정
        row_height = 60  # TODO: 주차별 행 높이 조정
        
        for week_idx, week in enumerate(weeks[:4]):  # 보통 4주차까지
            current_y = self._to_pdf_y(table_start_y + (week_idx * row_height))
            
            
            # 해당 주차의 업무들
            start_task = week_idx * tasks_per_week
            end_task = start_task + tasks_per_week
            week_tasks = report.tasks[start_task:end_task]
            
            if week_tasks:
                task_texts = [f"• {truncate_text(t.title, 30)}" for t in week_tasks[:3]]
                task_summary = "\n".join(task_texts)
                
                self.draw_multiline_text(
                    x=200,  # TODO: 좌표 조정
                    y=current_y,
                    text=task_summary,
                    font_size=9,
                    line_height=12
                )
        
        # ========================================
        # 익월 계획 (plans)
        # ========================================
        if report.plans:
            익월_계획 = "\n".join([f"• {plan}" for plan in report.plans[:5]])
            self.draw_multiline_text(
                x=130,  # TODO: 좌표 조정
                y=self._to_pdf_y(720),
                text=익월_계획,
                font_size=10,
                line_height=14
            )
        
        
        self.save_overlay()
        
        if output_filename is None:
            output_filename = f"월간보고서_{report.owner}_{월}.pdf"
        
        # 월간 보고서 전용 디렉토리에 저장
        monthly_dir = self.OUTPUT_DIR / "monthly"
        monthly_dir.mkdir(parents=True, exist_ok=True)
        output_path = monthly_dir / output_filename
        pdf_bytes = self.merge_with_template(output_path)
        
        return pdf_bytes


def generate_monthly_pdf_from_json(report_json: dict, output_filename: Optional[str] = None) -> bytes:
    """JSON에서 직접 PDF 생성"""
    report = CanonicalReport(**report_json)
    generator = MonthlyReportPDFGenerator()
    return generator.generate(report, output_filename)

