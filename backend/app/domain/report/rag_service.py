"""
RAG Service for Daily Report Chatbot

일일보고서 RAG 챗봇 서비스 레이어
"""
from typing import Dict, Any, Optional
from datetime import date

from app.domain.report.rag_chain import ReportRAGChain


class ReportRAGService:
    """일일보고서 RAG 서비스"""
    
    def __init__(self):
        """초기화"""
        pass
    
    async def chat(
        self,
        owner: str,
        query: str,
        date_range: Optional[Dict[str, date]] = None
    ) -> Dict[str, Any]:
        """
        RAG 챗봇 대화 처리
        
        Args:
            owner: 작성자 이름
            query: 사용자 질문
            date_range: 날짜 범위 필터 (예: {"start": date(2025, 1, 1), "end": date(2025, 12, 31)})
            
        Returns:
            {
                "answer": str,  # LLM 응답
                "sources": List[Dict],  # 근거 문서 정보
                "has_results": bool  # 검색 결과 존재 여부
            }
        """
        # RAG 체인 생성
        chain = ReportRAGChain(owner=owner, top_k=5)
        
        # 응답 생성
        result = await chain.generate_response(query, date_range)
        
        return result

