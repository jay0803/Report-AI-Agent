"""
보고서 처리 서비스
PDF 파일을 읽어서 JSON 형식으로 변환하는 기능 제공
"""
import os
import json
import base64
import uuid
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime, date

import fitz  # PyMuPDF
from openai import OpenAI

from app.domain.report.core.schemas import (
    ReportType,
    DailyReportSchema,
    WeeklyReportSchema,
    MonthlyReportSchema
)
from app.domain.report.core.canonical_models import CanonicalReport
from app.domain.report.core.canonical_converter import (
    convert_daily_to_canonical,
    convert_weekly_to_canonical,
    convert_monthly_to_canonical
)


class ReportProcessingService:
    """보고서 처리 서비스"""
    
    # ========================================
    # 보고서 스키마 정의 (4종류)
    # ========================================
    DAILY_SCHEMA = """
{
  "문서제목": "일일 업무 보고서",
  "상단정보": { "작성일자": "", "성명": "" },
  "금일_진행_업무": "",
  "세부업무": [
    { "시간": "09:00 - 10:00", "업무내용": "", "비고": "" },
    { "시간": "10:00 - 11:00", "업무내용": "", "비고": "" },
    { "시간": "11:00 - 12:00", "업무내용": "", "비고": "" },
    { "시간": "12:00 - 13:00", "업무내용": "", "비고": "" },
    { "시간": "13:00 - 14:00", "업무내용": "", "비고": "" },
    { "시간": "14:00 - 15:00", "업무내용": "", "비고": "" },
    { "시간": "15:00 - 16:00", "업무내용": "", "비고": "" },
    { "시간": "16:00 - 17:00", "업무내용": "", "비고": "" },
    { "시간": "17:00 - 18:00", "업무내용": "", "비고": "" }
  ],
  "미종결_업무사항": "",
  "익일_업무계획": "",
  "특이사항": ""
}
"""

    WEEKLY_SCHEMA = """
{
  "문서제목": "주간 업무 보고서",
  "상단정보": { "작성일자": "", "성명": "" },
  "주간업무목표": [
    { "항목": "1)", "목표": "", "비고": "" },
    { "항목": "2)", "목표": "", "비고": "" },
    { "항목": "3)", "목표": "", "비고": "" }
  ],
  "요일별_세부_업무": {
    "월": { "업무내용": "", "비고": "" },
    "화": { "업무내용": "", "비고": "" },
    "수": { "업무내용": "", "비고": "" },
    "목": { "업무내용": "", "비고": "" },
    "금": { "업무내용": "", "비고": "" }
  },
  "주간_중요_업무": "",
  "특이사항": ""
}
"""

    MONTHLY_SCHEMA = """
{
  "문서제목": "월간 업무 보고서",
  "상단정보": { "월": "", "작성일자": "", "성명": "" },
  "월간_핵심_지표": {
    "신규_계약_건수": { "건수": "", "비고": "" },
    "유지_계약_건수": { "유지": "", "갱신": "", "미납_방지": "", "비고": "" },
    "상담_진행_건수": { "전화": "", "방문": "", "온라인": "", "비고": "" }
  },
  "주차별_세부_업무": {
    "1주": { "업무내용": "", "비고": "" },
    "2주": { "업무내용": "", "비고": "" },
    "3주": { "업무내용": "", "비고": "" },
    "4주": { "업무내용": "", "비고": "" },
    "5주": { "업무내용": "", "비고": "" }
  },
  "익월_계획": ""
}
"""

    SCHEMA_MAP = {
        ReportType.DAILY: DAILY_SCHEMA,
        ReportType.WEEKLY: WEEKLY_SCHEMA,
        ReportType.MONTHLY: MONTHLY_SCHEMA
    }

    def __init__(self, api_key: str = None):
        """
        서비스 초기화
        
        Args:
            api_key: OpenAI API 키 (None인 경우 환경변수에서 읽음)
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.client = OpenAI()

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[bytes]:
        """
        PDF를 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            dpi: 이미지 해상도 (기본값: 200)
            
        Returns:
            이미지 바이트 리스트
        """
        doc = fitz.open(pdf_path)
        images = []
        
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
        
        doc.close()
        return images

    def encode_b64(self, data: bytes) -> str:
        """
        바이트 데이터를 base64로 인코딩
        
        Args:
            data: 바이트 데이터
            
        Returns:
            base64 인코딩된 문자열
        """
        return base64.b64encode(data).decode("utf-8")

    def detect_report_type(self, images: List[bytes]) -> ReportType:
        """
        문서 타입 자동 감지
        
        Args:
            images: PDF에서 변환된 이미지 리스트
            
        Returns:
            감지된 보고서 타입
        """
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "너는 문서 종류를 분류하는 전문가다."}]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
이 문서가 어떤 보고서인지 판단하라.
반드시 아래 중 하나로만 답하라:

daily / weekly / monthly

단 한 단어만 출력하라.
"""
                    },
                    *[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{self.encode_b64(img)}"
                            }
                        }
                        for img in images
                    ]
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o",  # gpt-4.1은 gpt-4o로 변경
            messages=messages
        )

        doc_type_str = response.choices[0].message.content.strip().lower()
        
        # 문자열을 ReportType enum으로 변환
        try:
            return ReportType(doc_type_str)
        except ValueError:
            raise ValueError(f"문서 타입 감지 실패: {doc_type_str}")

    def extract_with_schema(self, images: List[bytes], schema: str) -> Dict[str, Any]:
        """
        스키마를 기반으로 PDF에서 정보 추출
        
        Args:
            images: PDF에서 변환된 이미지 리스트
            schema: 적용할 JSON 스키마
            
        Returns:
            추출된 JSON 데이터
        """
        prompt = f"""
PDF 내용을 아래 JSON 스키마에 정확히 채워 넣어 출력하라.

규칙:
1) 필드명, 계층, 구조 절대 변경 금지
2) 값 누락 시 "" 유지
3) 필드 추가 금지
4) OCR로 읽은 값만 넣기
5) JSON만 출력

스키마:
{schema}
"""

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "너는 PDF를 JSON 스키마로 변환하는 전문가다."}]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{self.encode_b64(img)}"}
                        }
                        for img in images
                    ]
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="gpt-4o",  # gpt-4.1은 gpt-4o로 변경
            messages=messages,
            response_format={"type": "json_object"}
        )

        json_str = response.choices[0].message.content
        return json.loads(json_str)

    def process_report(self, pdf_path: str) -> Tuple[ReportType, Dict[str, Any]]:
        """
        보고서 PDF 처리 (타입 감지 + 정보 추출)
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            (보고서 타입, 추출된 JSON 데이터) 튜플
        """
        # PDF를 이미지로 변환
        images = self.pdf_to_images(pdf_path)
        print(f"✅ PDF를 {len(images)}개 페이지로 변환했습니다.")

        # 문서 타입 감지
        report_type = self.detect_report_type(images)
        print(f"✅ 문서 타입 감지됨: {report_type.value}")

        # 해당 스키마 선택
        schema = self.SCHEMA_MAP[report_type]

        # 정보 추출
        print("⏳ 보고서 정보 추출 중...")
        json_data = self.extract_with_schema(images, schema)
        print("✅ 보고서 정보 추출 완료!")

        return report_type, json_data

    # ========================================
    # Raw JSON → Canonical JSON 변환 함수들
    # ========================================
    
    def _parse_date(self, date_str: str) -> date | None:
        """날짜 문자열을 date 객체로 변환"""
        if not date_str or date_str.strip() == "":
            return None
        
        # 다양한 날짜 형식 처리
        formats = ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y년 %m월 %d일"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def normalize_daily(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        일일 보고서 Raw JSON → Canonical 변환 (새 구조 사용)
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # Raw 스키마로 변환
        daily_schema = DailyReportSchema(**raw_json)
        
        # 새 Canonical 변환기 사용
        return convert_daily_to_canonical(daily_schema)

    def normalize_weekly(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        주간 보고서 Raw JSON → Canonical 변환 (새 구조 사용)
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # Raw 스키마로 변환
        weekly_schema = WeeklyReportSchema(**raw_json)
        
        # 새 Canonical 변환기 사용
        return convert_weekly_to_canonical(weekly_schema)

    def normalize_monthly(self, raw_json: Dict[str, Any]) -> CanonicalReport:
        """
        월간 보고서 Raw JSON → Canonical 변환 (새 구조 사용)
        
        Args:
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
        """
        # Raw 스키마로 변환
        monthly_schema = MonthlyReportSchema(**raw_json)
        
        # 새 Canonical 변환기 사용
        return convert_monthly_to_canonical(monthly_schema)

    def normalize_report(
        self, 
        report_type: ReportType | str, 
        raw_json: Dict[str, Any]
    ) -> CanonicalReport:
        """
        보고서 타입에 따라 적절한 normalize 함수 호출
        
        Args:
            report_type: 보고서 타입
            raw_json: Vision API로부터 받은 원본 JSON
            
        Returns:
            CanonicalReport 객체
            
        Raises:
            ValueError: 지원하지 않는 보고서 타입인 경우
        """
        # ReportType enum을 문자열로 변환
        if isinstance(report_type, ReportType):
            report_type_str = report_type.value
        else:
            report_type_str = report_type
        
        # 타입별 normalize 함수 매핑
        normalize_map = {
            "daily": self.normalize_daily,
            "weekly": self.normalize_weekly,
            "monthly": self.normalize_monthly
        }
        
        normalize_func = normalize_map.get(report_type_str)
        if not normalize_func:
            raise ValueError(f"지원하지 않는 보고서 타입: {report_type_str}")
        
        return normalize_func(raw_json)

