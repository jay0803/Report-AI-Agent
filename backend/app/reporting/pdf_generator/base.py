"""
PDF Generator Base Class

ReportLab + PyPDF2를 사용하여 템플릿 PDF 위에 텍스트를 좌표 기반으로 삽입
"""
from pathlib import Path
from typing import Optional, Tuple
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter


class BasePDFGenerator:
    """PDF 생성 기본 클래스"""
    
    # A4 크기 (points)
    PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 x 841.89 points
    
    # 프로젝트 루트 찾기 (backend/app/reporting/pdf_generator/base.py -> backend/)
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    
    # 기본 템플릿 경로 (절대 경로)
    TEMPLATE_DIR = _BASE_DIR / "Data" / "reports"
    OUTPUT_DIR = _BASE_DIR / "output" / "report_result"
    
    def __init__(self, template_filename: str):
        """
        Args:
            template_filename: 템플릿 PDF 파일명 (예: "일일 업무 보고서.pdf")
        """
        self.template_path = self.TEMPLATE_DIR / template_filename
        self.overlay_buffer = BytesIO()
        self.canvas = None
        
        # 출력 디렉토리 생성
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 템플릿 파일 존재 확인
        if not self.template_path.exists():
            print(f"⚠️  템플릿 파일을 찾을 수 없습니다: {self.template_path}")
            print(f"   템플릿 디렉토리: {self.TEMPLATE_DIR}")
            print(f"   확인해주세요: backend/Data/reports/{template_filename}")
        
    def _init_canvas(self):
        """ReportLab Canvas 초기화"""
        self.canvas = canvas.Canvas(self.overlay_buffer, pagesize=A4)
        
        # 한글 폰트 등록 (시스템 폰트 사용)
        try:
            # Windows: 맑은 고딕
            pdfmetrics.registerFont(TTFont('malgun', 'C:/Windows/Fonts/malgun.ttf'))
            self.default_font = 'malgun'
        except:
            try:
                # Mac/Linux: NanumGothic 또는 기본 폰트
                pdfmetrics.registerFont(TTFont('NanumGothic', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'))
                self.default_font = 'NanumGothic'
            except:
                # 기본 폰트 사용 (한글 깨질 수 있음)
                self.default_font = 'Helvetica'
                print("⚠️  한글 폰트를 찾을 수 없어 기본 폰트 사용 (한글 깨질 수 있음)")
    
    def draw_text(
        self, 
        x: float, 
        y: float, 
        text: str, 
        font_size: int = 10,
        font_name: Optional[str] = None,
        color: Tuple[float, float, float] = (0, 0, 0)
    ):
        """
        지정된 좌표에 텍스트 그리기
        
        Args:
            x: X 좌표 (왼쪽 = 0, 오른쪽 = PAGE_WIDTH)
            y: Y 좌표 (아래 = 0, 위 = PAGE_HEIGHT)
            text: 출력할 텍스트
            font_size: 폰트 크기
            font_name: 폰트 이름 (None이면 기본 폰트)
            color: RGB 색상 튜플 (0~1)
        
        Note:
            PDF 좌표계는 왼쪽 아래가 원점(0, 0)
            Y축이 아래에서 위로 증가
        """
        if not self.canvas:
            raise ValueError("Canvas가 초기화되지 않았습니다. _init_canvas()를 먼저 호출하세요.")
        
        font = font_name or self.default_font
        self.canvas.setFont(font, font_size)
        self.canvas.setFillColorRGB(*color)
        self.canvas.drawString(x, y, str(text))
    
    def draw_multiline_text(
        self,
        x: float,
        y: float,
        text: str,
        font_size: int = 10,
        line_height: Optional[float] = None,
        max_width: Optional[float] = None,
        font_name: Optional[str] = None,
        color: Tuple[float, float, float] = (0, 0, 0)
    ):
        """
        여러 줄 텍스트 그리기 (자동 줄바꿈 지원)
        
        Args:
            x: X 좌표
            y: Y 좌표 (첫 줄 시작)
            text: 출력할 텍스트 (\n으로 줄바꿈)
            font_size: 폰트 크기
            line_height: 줄 간격 (None이면 font_size * 1.2)
            max_width: 최대 너비 (자동 줄바꿈용, None이면 무제한)
            font_name: 폰트 이름
            color: RGB 색상
        """
        if not self.canvas:
            raise ValueError("Canvas가 초기화되지 않았습니다.")
        
        if line_height is None:
            line_height = font_size * 1.2
        
        font = font_name or self.default_font
        self.canvas.setFont(font, font_size)
        self.canvas.setFillColorRGB(*color)
        
        # 줄바꿈 처리
        lines = text.split('\n')
        current_y = y
        
        for line in lines:
            if max_width:
                # TODO: 자동 줄바꿈 로직 (긴 텍스트를 max_width에 맞춰 분할)
                # 현재는 단순히 그대로 출력
                pass
            
            self.canvas.drawString(x, current_y, line)
            current_y -= line_height
    
    def draw_table_text(
        self,
        x: float,
        y: float,
        rows: list,
        col_widths: list,
        row_height: float = 20,
        font_size: int = 9
    ):
        """
        표 형식 텍스트 그리기
        
        Args:
            x: 표 시작 X 좌표
            y: 표 시작 Y 좌표 (위쪽)
            rows: 행 데이터 리스트 [['col1', 'col2'], ['val1', 'val2']]
            col_widths: 각 열의 너비 리스트
            row_height: 행 높이
            font_size: 폰트 크기
        """
        if not self.canvas:
            raise ValueError("Canvas가 초기화되지 않았습니다.")
        
        current_y = y
        
        for row in rows:
            current_x = x
            for i, cell_text in enumerate(row):
                col_width = col_widths[i] if i < len(col_widths) else 100
                self.draw_text(current_x, current_y, str(cell_text), font_size=font_size)
                current_x += col_width
            current_y -= row_height
    
    def save_overlay(self):
        """Overlay PDF 저장 (메모리 버퍼)"""
        if not self.canvas:
            raise ValueError("Canvas가 초기화되지 않았습니다.")
        
        self.canvas.save()
        self.overlay_buffer.seek(0)
    
    def merge_with_template(self, output_path: Optional[Path] = None) -> bytes:
        """
        템플릿 PDF와 overlay PDF를 병합
        
        Args:
            output_path: 출력 파일 경로 (None이면 저장하지 않음)
            
        Returns:
            PDF 바이트 스트림
        """
        # 템플릿 PDF 로드
        if not self.template_path.exists():
            raise FileNotFoundError(f"템플릿 PDF를 찾을 수 없습니다: {self.template_path}")
        
        template_pdf = PdfReader(str(self.template_path))
        overlay_pdf = PdfReader(self.overlay_buffer)
        
        # 새 PDF 작성기
        writer = PdfWriter()
        
        # 첫 페이지만 병합 (다중 페이지는 추후 확장 가능)
        template_page = template_pdf.pages[0]
        overlay_page = overlay_pdf.pages[0]
        
        # Overlay를 템플릿 위에 병합
        template_page.merge_page(overlay_page)
        writer.add_page(template_page)
        
        # 출력
        output_buffer = BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        pdf_bytes = output_buffer.read()
        
        # 파일로 저장 (옵션)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"✅ PDF 저장 완료: {output_path}")
        
        return pdf_bytes
    
    def generate(self, output_filename: Optional[str] = None) -> bytes:
        """
        PDF 생성 메인 함수 (하위 클래스에서 오버라이드)
        
        Args:
            output_filename: 출력 파일명 (None이면 저장하지 않음)
            
        Returns:
            PDF 바이트 스트림
        """
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")
    
    def _to_pdf_y(self, y: float) -> float:
        """
        상단 기준 Y 좌표를 PDF 좌표로 변환
        
        일반적으로 상단에서부터 거리를 지정하기 편하므로
        (0 = 최상단, PAGE_HEIGHT = 최하단)을 
        PDF 좌표계(0 = 최하단, PAGE_HEIGHT = 최상단)로 변환
        
        Args:
            y: 상단 기준 Y 좌표
            
        Returns:
            PDF 좌표계 Y 값
        """
        return self.PAGE_HEIGHT - y

