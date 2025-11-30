"""
KPI 문서 Vision 처리 서비스

PDF 파일을 읽어서 GPT-4o Vision으로 페이지별 구조화
"""
import os
import json
import base64
from typing import List
from pathlib import Path

import fitz  # PyMuPDF
from openai import OpenAI

from app.domain.kpi.schemas import KPIRawDocument, KPIPage, KPIRawItem


class KPIVisionService:
    """KPI 문서 Vision 처리 서비스"""
    
    # Vision 추출 스키마 (프롬프트용)
    KPI_SCHEMA = """
{
  "page_index": 0,
  "KPI_항목": [
    {
      "kpi_name": "",
      "category": "",
      "unit": "",
      "values": "",
      "delta": "",
      "설명": ""
    }
  ],
  "표": [],
  "텍스트요약": ""
}
"""
    
    def __init__(self, api_key: str = None):
        """
        서비스 초기화
        
        Args:
            api_key: OpenAI API 키 (None인 경우 환경변수에서 읽음)
        """
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        self.client = OpenAI()
        self.model = "gpt-4o"
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[bytes]:
        """
        PDF를 페이지별 이미지로 변환
        
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
        print(f"✅ PDF를 {len(images)}개 페이지로 변환했습니다.")
        return images
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """
        이미지를 base64로 인코딩
        
        Args:
            image_bytes: 이미지 바이트
            
        Returns:
            base64 인코딩된 문자열
        """
        return base64.b64encode(image_bytes).decode("utf-8")
    
    def extract_page(self, img_bytes: bytes, page_index: int) -> KPIPage:
        """
        페이지 이미지에서 KPI 정보 추출
        
        Args:
            img_bytes: 페이지 이미지 바이트
            page_index: 페이지 인덱스 (0부터 시작)
            
        Returns:
            KPIPage 객체
        """
        print(f"⏳ 페이지 {page_index + 1} 처리 중...")
        
        try:
            # base64 인코딩
            image_base64 = self._encode_image(img_bytes)
            
            # 프롬프트 구성
            prompt = f"""
다음 페이지에서 KPI 관련 정보를 최대한 구조화해서, 지정한 JSON 스키마에 채워 넣어라.

규칙:
1) 필드명과 구조는 절대 변경 금지
2) 값을 찾을 수 없으면 빈 문자열("") 유지
3) 표나 그래프에서 읽을 수 있는 숫자는 최대한 정확하게 추출
4) KPI 항목이 여러 개면 모두 추출
5) 표 데이터는 구조를 유지하면서 dict나 list로 저장
6) 텍스트요약은 페이지의 핵심 내용을 간단히 요약
7) JSON만 출력 (다른 텍스트 출력 금지)

스키마:
{self.KPI_SCHEMA}

page_index는 {page_index}로 설정하라.
"""
            
            # Vision API 호출
            messages = [
                {
                    "role": "system",
                    "content": "너는 보험사 KPI 문서를 구조화하는 전문가다. JSON 스키마에 맞춰 정확하게 데이터를 추출하라."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            # 응답 파싱
            json_str = response.choices[0].message.content
            json_data = json.loads(json_str)
            
            # KPIPage 객체 생성
            kpi_page = KPIPage(**json_data)
            print(f"✅ 페이지 {page_index + 1} 완료 (KPI {len(kpi_page.kpi_items)}개)")
            
            return kpi_page
            
        except Exception as e:
            print(f"❌ 페이지 {page_index + 1} 처리 오류: {str(e)}")
            # Fallback: 오류 페이지 반환
            return KPIPage(
                page_index=page_index,
                kpi_items=[],
                tables=[],
                text_summary="",
                error=str(e)
            )
    
    def process_pdf(self, pdf_path: str, title: str = "보험사 KPI 자료") -> KPIRawDocument:
        """
        PDF 파일 전체를 처리하여 KPIRawDocument 생성
        
        Args:
            pdf_path: PDF 파일 경로
            title: 문서 제목 (기본값: "보험사 KPI 자료")
            
        Returns:
            KPIRawDocument 객체
        """
        print("=" * 60)
        print(f"📄 KPI 문서 처리 시작: {pdf_path}")
        print("=" * 60)
        
        # PDF를 이미지로 변환
        images = self.pdf_to_images(pdf_path)
        total_pages = len(images)
        
        # 각 페이지 처리
        pages = []
        for idx, img_bytes in enumerate(images):
            kpi_page = self.extract_page(img_bytes, idx)
            pages.append(kpi_page)
        
        # KPIRawDocument 생성
        raw_document = KPIRawDocument(
            title=title,
            total_pages=total_pages,
            pages=pages
        )
        
        print()
        print("=" * 60)
        print("✅ KPI 문서 처리 완료")
        print("=" * 60)
        print(f"총 페이지: {total_pages}")
        print(f"총 KPI 항목: {sum(len(p.kpi_items) for p in pages)}")
        print()
        
        return raw_document

