"""
Plan API 엔드포인트

일정 계획 및 추천 API

Author: AI Assistant
Created: 2025-11-18
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import date
from sqlalchemy.orm import Session

from app.domain.planner.schemas import TodayPlanRequest, TodayPlanResponse
from app.domain.planner.today_plan_chain import TodayPlanGenerator
from app.domain.planner.tools import YesterdayReportTool
from app.domain.search.retriever import UnifiedRetriever
from app.infrastructure.database.session import get_db
from app.llm.client import get_llm
from app.core.config import settings


router = APIRouter(prefix="/plan", tags=["plan"])


def get_today_plan_generator(db: Session = Depends(get_db)) -> TodayPlanGenerator:
    """TodayPlanGenerator 의존성 주입"""
    # PostgreSQL에서 전날 데이터 조회
    retriever_tool = YesterdayReportTool(db)
    
    # VectorDB에서 유사 업무 패턴 검색 (선택적)
    vector_retriever = None
    try:
        # daily_reports_advanced 컬렉션 사용 (로컬 ChromaDB)
        from app.infrastructure.vector_store_advanced import get_vector_store
        vector_store = get_vector_store()
        collection = vector_store.get_collection()
        
        vector_retriever = UnifiedRetriever(
            collection=collection,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        doc_count = collection.count()
        print(f"✅ VectorDB 초기화 완료: daily_reports_advanced 컬렉션 ({doc_count}개 문서)")
    except Exception as e:
        print(f"[WARNING] VectorDB 초기화 실패 (추천 기능 제한): {e}")
        import traceback
        traceback.print_exc()
        # VectorDB가 없어도 작동하도록 None으로 설정
        vector_retriever = None
    
    llm_client = get_llm(model="gpt-4o-mini", temperature=0.7)
    
    return TodayPlanGenerator(retriever_tool, llm_client, vector_retriever)


@router.post("/today", response_model=TodayPlanResponse)
async def generate_today_plan(
    request: TodayPlanRequest,
    generator: TodayPlanGenerator = Depends(get_today_plan_generator)
) -> TodayPlanResponse:
    """
    오늘의 추천 일정 생성
    
    전날의 미종결 업무와 익일 계획을 기반으로
    오늘 하루 추천 일정을 AI가 자동 생성합니다.
    
    Args:
        request: 일정 생성 요청
        
    Returns:
        생성된 일정
    """
    try:
        result = await generator.generate(request)
        return result
    
    except Exception as e:
        print(f"[ERROR] Today plan generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"일정 생성 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check 엔드포인트"""
    return {"status": "ok", "service": "plan"}

