"""
Daily Report PDF Generator

일일보고서를 PDF로 생성
템플릿: backend/Data/reports/일일 업무 보고서.pdf
"""
from datetime import date
from typing import Optional
from pathlib import Path

from app.reporting.pdf_generator.base import BasePDFGenerator
from app.reporting.pdf_generator.utils import format_korean_date, truncate_text
from app.domain.report.schemas import CanonicalReport
import re


def clean_task_description(text: str) -> str:
    """
    업무 설명을 간결하게 정리
    
    예: "대상자 리스트를 업데이트합니다" → "대상자 리스트 업데이트"
        "자료를 점검하는" → "자료 점검"
    """
    if not text:
        return text
    
    result = text
    
    # 1. 종결어미 제거 (합니다, 입니다, 습니다, 함, 임)
    result = re.sub(r'(합니다|입니다|습니다)\.?$', '', result)
    result = re.sub(r'(함|임)\.?$', '', result)
    
    # 2. "~하고 ... 합니다/진행함" 패턴 → "~하고 ... 진행"
    result = re.sub(r'하고\s+(\S+)\s+(진행|수행|실시)합니다?', r'하고 \1 \2', result)
    result = re.sub(r'하고\s+(\S+)\s+(진행|수행|실시)함', r'하고 \1 \2', result)
    
    # 3. "~를/을 [동사]합니다" → "[동사]"
    result = re.sub(r'(을|를)\s+(\S+)합니다\.?$', r'\2', result)
    result = re.sub(r'(을|를)\s+(\S+)함\.?$', r'\2', result)
    
    # 4. "~하는" 형태 제거
    result = re.sub(r'하는$', '', result)
    result = re.sub(r'하는\s+(작업|업무)', '', result)
    result = re.sub(r'(을|를)\s+(\S+)하는', r'\2', result)
    result = re.sub(r'(\S+)하는', r'\1', result)
    
    # 5. "~니다" 종결 제거
    result = re.sub(r'니다\.?$', '', result)
    
    # 6. "작업", "업무" 제거
    result = re.sub(r'\s*(작업|업무)\.?$', '', result)
    
    # 7. 마침표, 쉼표 제거
    result = re.sub(r'[.,;]+$', '', result)
    
    # 8. 연속된 공백 제거 및 앞뒤 공백 제거
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result


class DailyReportPDFGenerator(BasePDFGenerator):
    """일일보고서 PDF 생성기"""
    
    def __init__(self):
        # 템플릿 파일명 (실제 파일명에 맞게 수정 필요)
        super().__init__("일일 업무 보고서.pdf")
    
    def generate(
        self, 
        report: CanonicalReport,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        일일보고서 PDF 생성
        
        Args:
            report: CanonicalReport 객체 (daily 타입)
            output_filename: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            PDF 바이트 스트림
        """
        print(f"📄 일일보고서 PDF 생성 시작")
        print(f"   Owner: {report.owner}, Date: {report.period_start}")
        print(f"   Tasks: {len(report.tasks)}개, Issues: {len(report.issues)}개")
        
        # Canvas 초기화
        self._init_canvas()
        
        # ========================================
        # 상단 정보 (font 11pt)
        # 작성자 / 작성일자 / 성명
        # ========================================
        작성일자 = format_korean_date(report.period_start)
        성명 = report.owner
        
        self.draw_text(172, self._to_pdf_y(105), 작성일자, font_size=10)
        self.draw_text(340, self._to_pdf_y(105), 성명, font_size=10)
        
        # ========================================
        # 금일 진행 업무 (font 10pt, line spacing 22px)
        # y = 235, 257, 279 (최대 3줄)
        # ========================================
        금일_진행_업무_list = []
        
        # plans (예정 업무) 포함
        if report.plans:
            for idx, plan in enumerate(report.plans, 1):
                plan_text = plan if isinstance(plan, str) else plan.get('title', str(plan))
                금일_진행_업무_list.append(f"{idx}. {plan_text}")
        
        # summary 추가
        summary = report.metadata.get('summary', '')
        if summary:
            금일_진행_업무_list.append(summary)
        
        # Y 좌표 배열 (보정된 좌표)
        금일_진행_업무_y_positions = [165, 187, 209]
        
        for idx, line in enumerate(금일_진행_업무_list[:3]):
            if idx < len(금일_진행_업무_y_positions):
                self.draw_text(
                    x=195,
                    y=self._to_pdf_y(금일_진행_업무_y_positions[idx]),
                    text=truncate_text(line, max_length=80),
                    font_size=10
                )
        
        # ========================================
        # 세부업무 표 (font 9pt)
        # 시간은 출력하지 않음 (템플릿에 이미 인쇄됨)
        # 업무내용 x=260, 비고 x=620
        # ========================================
        # 시간대별 Y 좌표 맵핑 (보정된 좌표 +25px)
        time_slot_y_positions = [
            265,  # 09:00
            295,  # 10:00
            325,  # 11:00
            350,  # 12:00
            380,  # 13:00
            410,  # 14:00
            440,  # 15:00
            465,  # 16:00
            495   # 17:00
        ]
        
        # 최대 9개 업무 표시
        tasks = report.tasks[:9] if len(report.tasks) > 9 else report.tasks
        
        for idx, task in enumerate(tasks):
            if idx >= len(time_slot_y_positions):
                break
            
            y_pos = time_slot_y_positions[idx]
            
            # 업무내용 (좌측 정렬)
            업무내용 = task.description or task.title
            업무내용 = clean_task_description(업무내용)  # 간결하게 정리
            업무내용 = truncate_text(업무내용, max_length=32)
            
            self.draw_text(
                x=195,
                y=self._to_pdf_y(y_pos),
                text=업무내용,
                font_size=10
            )
            
            # 비고 (좌측 정렬)
            비고 = task.note or ""
            if 비고:
                # "카테고리: " 제거
                비고 = re.sub(r'^카테고리:\s*', '', 비고)
                비고 = truncate_text(비고, max_length=20)
                self.draw_text(
                    x=460,
                    y=self._to_pdf_y(y_pos),
                    text=비고,
                    font_size=9
                )
        
        # ========================================
        # 미종결 업무사항 (font 10pt)
        # x=150, y=835
        # ========================================
        if report.issues:
            미종결_업무 = "\n".join([f"• {issue}" for issue in report.issues])
            self.draw_multiline_text(
                x=195,
                y=self._to_pdf_y(535),
                text=미종결_업무,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 익일 업무계획 (font 10pt)
        # x=150, y=920
        # ========================================
        익일_업무계획_raw = report.metadata.get('next_day_plans', '') or report.metadata.get('next_plan', '')
        
        if isinstance(익일_업무계획_raw, list):
            익일_업무계획 = "\n".join([f"• {plan}" for plan in 익일_업무계획_raw]) if 익일_업무계획_raw else ""
        else:
            익일_업무계획 = str(익일_업무계획_raw) if 익일_업무계획_raw else ""
        
        if 익일_업무계획:
            self.draw_multiline_text(
                x=195,
                y=self._to_pdf_y(630),
                text=익일_업무계획,
                font_size=10,
                line_height=14
            )
        
        # ========================================
        # 특이사항 (font 10pt)
        # x=150, y=1005
        # ========================================
        특이사항 = report.metadata.get('notes', '')
        if 특이사항:
            self.draw_multiline_text(
                x=195,
                y=self._to_pdf_y(725),
                text=특이사항,
                font_size=10,
                line_height=14
            )
        
        # Overlay 저장
        self.save_overlay()
        
        # 템플릿과 병합
        if output_filename is None:
            output_filename = f"일일보고서_{report.owner}_{format_korean_date(report.period_start)}.pdf"
        
        # 일일 보고서 전용 디렉토리에 저장
        daily_dir = self.OUTPUT_DIR / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        output_path = daily_dir / output_filename
        
        print(f"📁 PDF 출력 경로: {output_path}")
        print(f"   템플릿 경로: {self.template_path}")
        
        pdf_bytes = self.merge_with_template(output_path)
        
        print(f"✅ PDF 생성 완료: {len(pdf_bytes)} bytes")
        
        return pdf_bytes


def generate_daily_pdf_from_json(report_json: dict, output_filename: Optional[str] = None) -> bytes:
    """
    JSON에서 직접 PDF 생성 (편의 함수)
    
    Args:
        report_json: CanonicalReport JSON dict
        output_filename: 출력 파일명
        
    Returns:
        PDF 바이트 스트림
    """
    report = CanonicalReport(**report_json)
    generator = DailyReportPDFGenerator()
    return generator.generate(report, output_filename)

