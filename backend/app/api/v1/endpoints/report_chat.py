"""
Report Chat API Endpoints

일일보고서 RAG 챗봇 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date

from app.domain.report.core.rag_service import ReportRAGService

router = APIRouter(prefix="/report-chat", tags=["report-chat"])

# RAG 서비스 인스턴스 (lazy initialization)
_rag_service: Optional[ReportRAGService] = None


def get_rag_service() -> ReportRAGService:
    """ReportRAGService 싱글톤 인스턴스 반환 (lazy initialization)"""
    global _rag_service
    if _rag_service is None:
        _rag_service = ReportRAGService()
    return _rag_service


class ChatRequest(BaseModel):
    """챗봇 질문 요청"""
    owner: str
    query: str
    date_start: Optional[str] = None  # YYYY-MM-DD 형식
    date_end: Optional[str] = None  # YYYY-MM-DD 형식
    reference_date: Optional[str] = None  # YYYY-MM-DD 형식, "이번 주" 같은 상대적 날짜 계산 기준


class SourceInfo(BaseModel):
    """근거 문서 정보"""
    date: str
    time_slot: Optional[str] = None
    chunk_type: str
    category: Optional[str] = None
    text_preview: str
    score: float


class ChatResponse(BaseModel):
    """챗봇 응답"""
    answer: str
    sources: List[SourceInfo]
    has_results: bool


@router.post("/chat", response_model=ChatResponse)
async def chat_with_reports(request: ChatRequest):
    """
    일일보고서 데이터 기반 RAG 챗봇 대화
    
    Args:
        request: ChatRequest (owner, query, date_start, date_end)
        
    Returns:
        ChatResponse (answer, sources, has_results)
        
    예시:
        - "나 최근에 연금 상담 언제 했었지?"
        - "최근에 상담했던 암보험 고객 이름 누구였지?"
        - "지난달에 실손 갱신 상담한 적 있었어?"
        - "올해 들어 내가 가장 많이 상담한 보험 종류가 뭐야?"
        - "지난주에 처리 못한 미종결 업무 뭐 있었지?"
    """
    try:
        # 날짜 범위 파싱
        date_range = None
        if request.date_start or request.date_end:
            date_range = {}
            if request.date_start:
                date_range["start"] = date.fromisoformat(request.date_start)
            if request.date_end:
                date_range["end"] = date.fromisoformat(request.date_end)
        
        # 기준 날짜 파싱 (상대적 날짜 계산용)
        reference_date = None
        if request.reference_date:
            reference_date = date.fromisoformat(request.reference_date)
        
        # RAG 서비스 호출
        rag_service = get_rag_service()
        result = await rag_service.chat(
            owner=request.owner,
            query=request.query,
            date_range=date_range,
            reference_date=reference_date
        )
        
        # SourceInfo 변환
        sources = [
            SourceInfo(**source) for source in result["sources"]
        ]
        
        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            has_results=result["has_results"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"날짜 형식 오류: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Report chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"챗봇 처리 중 오류: {str(e)}")

