"""
Intent Router

LLM을 사용하여 사용자 질의의 의도를 분석하고 라우팅합니다.

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field
import openai
import json
import os


class QueryIntent(BaseModel):
    """쿼리 의도 분석 결과"""
    intent: Literal["daily", "weekly", "monthly", "kpi", "template", "mixed", "unknown"] = Field(
        ...,
        description="질의 의도"
    )
    reason: str = Field(..., description="판단 근거")
    filters: dict = Field(default_factory=dict, description="추출된 필터 정보")


class IntentRouter:
    """LLM 기반 Intent Router"""
    
    SYSTEM_PROMPT = """당신은 사용자의 질의를 분석하여 적절한 문서 타입으로 라우팅하는 AI 어시스턴트입니다.

사용자의 질문을 분석하여 다음 중 하나의 의도(intent)로 분류하세요:

1. **daily** (일일 보고서)
   - 특정 날짜의 업무 내용, 일정, 작업 로그를 묻는 질문
   - 예: "11월 12일 뭐 했는지 알려줘", "어제 업무 내용 정리해줘"

2. **weekly** (주간 기간 질문 - daily 문서를 날짜 범위로 검색)
   - 특정 주의 업무 내용을 묻는 질문 (실제로는 daily 타입 문서들을 기간으로 검색)
   - ⚠️ 주의: 이런 질문은 "daily"로 분류하고 filters에 기간 정보를 포함하세요
   - 예: "11월 둘째 주에 신규 고객 관련해서 뭐 했는지 알려줘" → intent="daily", filters={"period": "2025-11-04~2025-11-10"}

3. **monthly** (월간 보고서)
   - 특정 월의 업무 내용을 묻는 질문
   - 예: "11월 업무 내용 정리해줘"

4. **template**
   - 양식, 템플릿, 서식, 폼, 예시 문서를 묻는 질문
   - 예: "월간 업무 보고서 양식 보여줘"

6. **mixed**
   - 여러 의도가 섞여 있는 질문
   - 예: "11월 업무 내용과 KPI 모두 보여줘"

7. **unknown**
   - 위 카테고리에 해당하지 않는 질문

응답은 반드시 다음 JSON 형식으로만 반환하세요:
{
  "intent": "daily|weekly|monthly|kpi|template|mixed|unknown",
  "reason": "판단 근거 설명",
  "filters": {
    "owner": "작성자 (선택)",
    "date": "날짜 YYYY-MM-DD (선택)",
    "category": "카테고리 (선택)"
  }
}
"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        초기화
        
        Args:
            api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            model: LLM 모델명
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def route(self, query: str) -> QueryIntent:
        """
        질의 의도 분석 및 라우팅
        
        Args:
            query: 사용자 질의
            
        Returns:
            QueryIntent 객체
        """
        try:
            # LLM 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"질문: {query}"}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            # 응답 파싱
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                # JSON 블록 추출 (```json ... ``` 형식 처리)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result_dict = json.loads(content)
                
                return QueryIntent(
                    intent=result_dict.get("intent", "unknown"),
                    reason=result_dict.get("reason", ""),
                    filters=result_dict.get("filters", {})
                )
            
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 intent 추출 시도
                content_lower = content.lower()
                
                if "daily" in content_lower:
                    intent = "daily"
                elif "weekly" in content_lower:
                    intent = "weekly"
                elif "monthly" in content_lower:
                    intent = "monthly"
                elif "kpi" in content_lower:
                    intent = "kpi"
                elif "template" in content_lower:
                    intent = "template"
                elif "mixed" in content_lower:
                    intent = "mixed"
                else:
                    intent = "unknown"
                
                return QueryIntent(
                    intent=intent,
                    reason=content,
                    filters={}
                )
        
        except Exception as e:
            print(f"❌ Intent 분석 오류: {e}")
            return QueryIntent(
                intent="unknown",
                reason=f"오류 발생: {str(e)}",
                filters={}
            )

